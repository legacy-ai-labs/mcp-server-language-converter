"""Data Flow Graph (DFG) builder service for COBOL programs.

This module builds a Data Flow Graph from a COBOL AST (ParseNode).
The DFG tracks how data flows through the program and enables:
- Dead variable detection (assigned but never read)
- Uninitialized variable detection (read before assignment)
- Data dependency analysis for refactoring
- Understanding data transformations for migration

The DFG is built from the AST, analyzing MOVE, COMPUTE, ADD, and other
data manipulation statements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.core.services.cobol_analysis.cobol_parser_antlr_service import ParseNode


logger = logging.getLogger(__name__)


class DFGNodeType(str, Enum):
    """Types of nodes in the Data Flow Graph."""

    DEFINITION = "DEFINITION"  # Variable definition (DATA DIVISION)
    ASSIGNMENT = "ASSIGNMENT"  # Variable assigned a value
    READ = "READ"  # Variable read
    PARAMETER_IN = "PARAMETER_IN"  # Input parameter
    PARAMETER_OUT = "PARAMETER_OUT"  # Output parameter
    EXTERNAL_INPUT = "EXTERNAL_INPUT"  # READ from file
    EXTERNAL_OUTPUT = "EXTERNAL_OUTPUT"  # WRITE to file


class DFGEdgeType(str, Enum):
    """Types of edges in the Data Flow Graph."""

    DEF_USE = "DEF_USE"  # Definition to use
    USE_DEF = "USE_DEF"  # Use to definition
    DATA_DEPENDENCY = "DATA_DEPENDENCY"  # Data flows from source to target
    CONTROL_DEPENDENCY = "CONTROL_DEPENDENCY"  # Data flow depends on control


class DFGNode(BaseModel):
    """A node in the Data Flow Graph."""

    id: str = Field(description="Unique node identifier")
    node_type: DFGNodeType = Field(description="Type of DFG node")
    variable_name: str = Field(description="Variable name involved")
    label: str = Field(description="Human-readable label")
    ast_node_id: int | None = Field(default=None, description="Reference to AST node")
    line_number: int | None = Field(default=None, description="Source line number")
    statement_type: str | None = Field(default=None, description="Type of statement")


class DFGEdge(BaseModel):
    """An edge in the Data Flow Graph."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    edge_type: DFGEdgeType = Field(description="Type of data flow")
    variable: str = Field(description="Variable being tracked")


class VariableInfo(BaseModel):
    """Information about a variable's data flow."""

    name: str = Field(description="Variable name")
    level: int | None = Field(default=None, description="Data level (01-88)")
    picture: str | None = Field(default=None, description="PICTURE clause")
    definition_line: int | None = Field(default=None, description="Line where defined")
    assignments: list[int] = Field(default_factory=list, description="Lines where assigned")
    reads: list[int] = Field(default_factory=list, description="Lines where read")
    is_dead: bool = Field(default=False, description="Assigned but never read")
    is_uninitialized_read: bool = Field(default=False, description="Read before assignment")


class DataFlowGraph(BaseModel):
    """Complete Data Flow Graph for a COBOL program."""

    program_name: str | None = Field(default=None, description="Program identifier")
    nodes: list[DFGNode] = Field(default_factory=list, description="DFG nodes")
    edges: list[DFGEdge] = Field(default_factory=list, description="DFG edges")
    variables: dict[str, VariableInfo] = Field(
        default_factory=dict, description="Variable information"
    )

    # Computed metrics
    node_count: int = Field(default=0, description="Total nodes")
    edge_count: int = Field(default=0, description="Total edges")
    dead_variables: list[str] = Field(
        default_factory=list, description="Variables assigned but never read"
    )
    uninitialized_reads: list[str] = Field(
        default_factory=list, description="Variables read before assignment"
    )
    data_dependencies: int = Field(default=0, description="Number of data dependencies")


@dataclass
class DFGBuilderContext:
    """Context for building the DFG."""

    node_counter: int = 0
    nodes: dict[str, DFGNode] = field(default_factory=dict)
    edges: list[DFGEdge] = field(default_factory=list)
    variables: dict[str, VariableInfo] = field(default_factory=dict)

    # Track definitions and uses for each variable
    last_definition: dict[str, str] = field(default_factory=dict)  # var -> node_id
    uses_before_def: set[str] = field(default_factory=set)  # vars read before assign

    def next_node_id(self) -> str:
        """Generate next unique node ID."""
        self.node_counter += 1
        return f"d{self.node_counter}"


class DFGBuilderError(Exception):
    """Exception raised when DFG building fails."""

    pass


def build_dfg_from_ast(
    ast: ParseNode | dict[str, Any],
    program_name: str | None = None,
) -> DataFlowGraph:
    """Build a Data Flow Graph from a COBOL AST.

    Args:
        ast: ParseNode or dict representation of the AST
        program_name: Optional program name

    Returns:
        DataFlowGraph with nodes, edges, and computed metrics

    Raises:
        DFGBuilderError: If DFG construction fails
    """
    try:
        # Convert dict to ParseNode if needed
        if isinstance(ast, dict):
            ast = _dict_to_parse_node(ast)

        ctx = DFGBuilderContext()

        # Process DATA DIVISION to get variable definitions
        data_div = _find_node(ast, ["DATA_DIVISION", "DataDivision", "dataDivision"])
        if data_div:
            _process_data_division(data_div, ctx)

        # Process PROCEDURE DIVISION to track data flow
        procedure_div = _find_node(ast, ["PROCEDURE_DIVISION", "ProcedureDivision"])
        if procedure_div:
            _process_procedure_division_dfg(procedure_div, ctx)

        # Analyze variable usage
        _analyze_variable_usage(ctx)

        # Build the DFG
        dfg = DataFlowGraph(
            program_name=program_name,
            nodes=list(ctx.nodes.values()),
            edges=ctx.edges,
            variables=ctx.variables,
            node_count=len(ctx.nodes),
            edge_count=len(ctx.edges),
            data_dependencies=len(ctx.edges),
        )

        # Compute dead variables and uninitialized reads
        dfg.dead_variables = [name for name, info in ctx.variables.items() if info.is_dead]
        dfg.uninitialized_reads = [
            name for name, info in ctx.variables.items() if info.is_uninitialized_read
        ]

        logger.info(
            f"Built DFG: {dfg.node_count} nodes, {dfg.edge_count} edges, "
            f"{len(dfg.dead_variables)} dead variables, "
            f"{len(dfg.uninitialized_reads)} uninitialized reads"
        )

        return dfg

    except Exception as e:
        logger.exception("Failed to build DFG")
        raise DFGBuilderError(f"DFG construction failed: {e}") from e


def _dict_to_parse_node(node_dict: dict[str, Any]) -> ParseNode:
    """Convert dictionary to ParseNode."""
    children = [
        _dict_to_parse_node(child)
        for child in node_dict.get("children", [])
        if isinstance(child, dict)
    ]

    return ParseNode(
        type=node_dict.get("type", "Unknown"),
        children=children,
        value=node_dict.get("value"),
        start_line=node_dict.get("start_line"),
        start_column=node_dict.get("start_column"),
        end_line=node_dict.get("end_line"),
        end_column=node_dict.get("end_column"),
        id=node_dict.get("id"),
        rule_name=node_dict.get("rule_name"),
        text=node_dict.get("text"),
    )


def _find_node(node: ParseNode, type_names: list[str]) -> ParseNode | None:
    """Find a node by type name."""
    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        return node

    for child in node.children:
        result = _find_node(child, type_names)
        if result:
            return result

    return None


def _find_all_nodes(node: ParseNode, type_names: list[str]) -> list[ParseNode]:
    """Find all nodes matching type names."""
    results: list[ParseNode] = []

    if node.type in type_names or (node.rule_name and node.rule_name in type_names):
        results.append(node)

    for child in node.children:
        results.extend(_find_all_nodes(child, type_names))

    return results


def _process_data_division(data_div: ParseNode, ctx: DFGBuilderContext) -> None:
    """Process DATA DIVISION to extract variable definitions."""
    # Find all data entries
    data_entries = _find_all_nodes(
        data_div,
        [
            "DataDescriptionEntry",
            "dataDescriptionEntry",
            "DataDescriptionEntryFormat1",
            "dataDescriptionEntryFormat1",
            "DataDescriptionEntryFormat2",
        ],
    )

    for entry in data_entries:
        var_name = _extract_data_name(entry)
        if var_name:
            # Create definition node
            node_id = ctx.next_node_id()
            def_node = DFGNode(
                id=node_id,
                node_type=DFGNodeType.DEFINITION,
                variable_name=var_name,
                label=f"DEF {var_name}",
                ast_node_id=entry.id,
                line_number=entry.start_line,
                statement_type="DATA_DEFINITION",
            )
            ctx.nodes[node_id] = def_node

            # Store variable info
            level = _extract_level(entry)
            picture = _extract_picture(entry)

            ctx.variables[var_name] = VariableInfo(
                name=var_name,
                level=level,
                picture=picture,
                definition_line=entry.start_line,
            )

            ctx.last_definition[var_name] = node_id


def _process_procedure_division_dfg(proc_div: ParseNode, ctx: DFGBuilderContext) -> None:
    """Process PROCEDURE DIVISION to track data flow."""
    # Find data manipulation statements
    _process_move_statements(proc_div, ctx)
    _process_compute_statements(proc_div, ctx)
    _process_arithmetic_statements(proc_div, ctx)
    _process_read_write_statements(proc_div, ctx)
    _process_call_statements(proc_div, ctx)


def _process_move_statements(node: ParseNode, ctx: DFGBuilderContext) -> None:
    """Process MOVE statements."""
    move_stmts = _find_all_nodes(node, ["MoveStatement", "moveStatement", "MOVE_STATEMENT"])

    for stmt in move_stmts:
        # Extract source and target variables
        source_vars = _extract_source_variables(stmt)
        target_vars = _extract_target_variables(stmt)

        # Create read nodes for sources
        for var_name in source_vars:
            _record_variable_read(var_name, stmt, ctx)

        # Create assignment nodes for targets
        for var_name in target_vars:
            _record_variable_assignment(var_name, stmt, ctx, source_vars)


def _process_compute_statements(node: ParseNode, ctx: DFGBuilderContext) -> None:
    """Process COMPUTE statements."""
    compute_stmts = _find_all_nodes(
        node, ["ComputeStatement", "computeStatement", "COMPUTE_STATEMENT"]
    )

    for stmt in compute_stmts:
        # In COMPUTE, variables on right side are read, left side is assigned
        target_vars = _extract_compute_targets(stmt)
        source_vars = _extract_compute_sources(stmt)

        for var_name in source_vars:
            _record_variable_read(var_name, stmt, ctx)

        for var_name in target_vars:
            _record_variable_assignment(var_name, stmt, ctx, source_vars)


def _process_arithmetic_statements(node: ParseNode, ctx: DFGBuilderContext) -> None:
    """Process ADD, SUBTRACT, MULTIPLY, DIVIDE statements."""
    arith_stmts = _find_all_nodes(
        node,
        [
            "AddStatement",
            "addStatement",
            "SubtractStatement",
            "subtractStatement",
            "MultiplyStatement",
            "multiplyStatement",
            "DivideStatement",
            "divideStatement",
        ],
    )

    for stmt in arith_stmts:
        # Extract variables involved
        all_vars = _extract_all_identifiers(stmt)

        # For arithmetic, operands are read, result is assigned
        # Simplified: treat all as both read and assigned
        for var_name in all_vars:
            _record_variable_read(var_name, stmt, ctx)
            _record_variable_assignment(var_name, stmt, ctx, all_vars)


def _process_read_write_statements(node: ParseNode, ctx: DFGBuilderContext) -> None:
    """Process READ and WRITE statements."""
    read_stmts = _find_all_nodes(node, ["ReadStatement", "readStatement"])
    write_stmts = _find_all_nodes(node, ["WriteStatement", "writeStatement"])

    for stmt in read_stmts:
        # READ assigns to a record/variable
        target_vars = _extract_all_identifiers(stmt)
        for var_name in target_vars:
            node_id = ctx.next_node_id()
            read_node = DFGNode(
                id=node_id,
                node_type=DFGNodeType.EXTERNAL_INPUT,
                variable_name=var_name,
                label=f"READ INTO {var_name}",
                ast_node_id=stmt.id,
                line_number=stmt.start_line,
                statement_type="READ",
            )
            ctx.nodes[node_id] = read_node

            if var_name in ctx.variables:
                ctx.variables[var_name].assignments.append(stmt.start_line or 0)
                ctx.last_definition[var_name] = node_id

    for stmt in write_stmts:
        # WRITE reads from a record/variable
        source_vars = _extract_all_identifiers(stmt)
        for var_name in source_vars:
            node_id = ctx.next_node_id()
            write_node = DFGNode(
                id=node_id,
                node_type=DFGNodeType.EXTERNAL_OUTPUT,
                variable_name=var_name,
                label=f"WRITE FROM {var_name}",
                ast_node_id=stmt.id,
                line_number=stmt.start_line,
                statement_type="WRITE",
            )
            ctx.nodes[node_id] = write_node

            if var_name in ctx.variables:
                ctx.variables[var_name].reads.append(stmt.start_line or 0)


def _process_call_statements(node: ParseNode, ctx: DFGBuilderContext) -> None:
    """Process CALL statements for parameter flow."""
    call_stmts = _find_all_nodes(node, ["CallStatement", "callStatement"])

    for stmt in call_stmts:
        # Parameters in USING clause
        params = _extract_call_parameters(stmt)

        for param in params:
            # Treat as both read and potentially modified (BY REFERENCE)
            _record_variable_read(param, stmt, ctx)


def _record_variable_read(var_name: str, stmt: ParseNode, ctx: DFGBuilderContext) -> None:
    """Record a variable read."""
    node_id = ctx.next_node_id()
    read_node = DFGNode(
        id=node_id,
        node_type=DFGNodeType.READ,
        variable_name=var_name,
        label=f"READ {var_name}",
        ast_node_id=stmt.id,
        line_number=stmt.start_line,
        statement_type=stmt.type,
    )
    ctx.nodes[node_id] = read_node

    # Record in variable info
    if var_name in ctx.variables:
        ctx.variables[var_name].reads.append(stmt.start_line or 0)
    else:
        # Variable used but not defined in DATA DIVISION
        # Could be a group item reference or external
        ctx.uses_before_def.add(var_name)

    # Create def-use edge if we have a definition
    if var_name in ctx.last_definition:
        ctx.edges.append(
            DFGEdge(
                source=ctx.last_definition[var_name],
                target=node_id,
                edge_type=DFGEdgeType.DEF_USE,
                variable=var_name,
            )
        )


def _record_variable_assignment(
    var_name: str,
    stmt: ParseNode,
    ctx: DFGBuilderContext,
    source_vars: list[str] | set[str],
) -> None:
    """Record a variable assignment."""
    node_id = ctx.next_node_id()
    assign_node = DFGNode(
        id=node_id,
        node_type=DFGNodeType.ASSIGNMENT,
        variable_name=var_name,
        label=f"ASSIGN {var_name}",
        ast_node_id=stmt.id,
        line_number=stmt.start_line,
        statement_type=stmt.type,
    )
    ctx.nodes[node_id] = assign_node

    # Record in variable info
    if var_name in ctx.variables:
        ctx.variables[var_name].assignments.append(stmt.start_line or 0)

    # Create data dependency edges from sources
    for source_var in source_vars:
        if source_var in ctx.last_definition:
            ctx.edges.append(
                DFGEdge(
                    source=ctx.last_definition[source_var],
                    target=node_id,
                    edge_type=DFGEdgeType.DATA_DEPENDENCY,
                    variable=f"{source_var} -> {var_name}",
                )
            )

    # Update last definition
    ctx.last_definition[var_name] = node_id


def _analyze_variable_usage(ctx: DFGBuilderContext) -> None:
    """Analyze variable usage to find dead variables and uninitialized reads."""
    for _var_name, var_info in ctx.variables.items():
        # Dead variable: assigned but never read
        if var_info.assignments and not var_info.reads:
            var_info.is_dead = True

        # Uninitialized read: read before any assignment
        # (Simplified: if first read line < first assignment line)
        if var_info.reads and var_info.assignments:
            first_read = min(var_info.reads)
            first_assign = min(var_info.assignments)
            if first_read < first_assign:
                var_info.is_uninitialized_read = True
        elif var_info.reads and not var_info.assignments:
            # Read but never assigned (relies on VALUE clause or external)
            # Mark as potential uninitialized if no VALUE clause
            var_info.is_uninitialized_read = True


def _extract_data_name(entry: ParseNode) -> str | None:
    """Extract data name from a data description entry."""
    # Look for dataName or identifier
    for child in entry.children:
        if child.type and "dataName" in child.type.lower():
            if child.value:
                return str(child.value)
            if child.text:
                return child.text
            # Check children
            for sub in child.children:
                if sub.text:
                    return sub.text

    return None


def _extract_level(entry: ParseNode) -> int | None:
    """Extract level number from a data description entry."""
    for child in entry.children:
        if child.type and "level" in child.type.lower() and child.text:
            try:
                return int(child.text)
            except ValueError:
                pass

    return None


def _extract_picture(entry: ParseNode) -> str | None:
    """Extract PICTURE clause from a data description entry."""
    pic_nodes = _find_all_nodes(entry, ["PictureClause", "pictureClause", "pictureString"])
    if pic_nodes:
        for pic in pic_nodes:
            if pic.text:
                return pic.text
            for child in pic.children:
                if child.text:
                    return child.text

    return None


def _extract_source_variables(stmt: ParseNode) -> list[str]:
    """Extract source variables from a MOVE statement."""
    vars_found: list[str] = []

    # In MOVE X TO Y, X is source
    # Look for identifier before TO keyword
    found_to = False
    for child in stmt.children:
        if child.text and child.text.upper() == "TO":
            found_to = True
            continue

        # Before TO - these are sources
        if not found_to and child.type and "identifier" in child.type.lower():
            name = _extract_identifier_name(child)
            if name:
                vars_found.append(name)

    return vars_found


def _extract_target_variables(stmt: ParseNode) -> list[str]:
    """Extract target variables from a MOVE statement."""
    vars_found: list[str] = []

    # In MOVE X TO Y Z, Y and Z are targets (after TO)
    found_to = False
    for child in stmt.children:
        if child.text and child.text.upper() == "TO":
            found_to = True
            continue

        # After TO - these are targets
        if found_to and child.type and "identifier" in child.type.lower():
            name = _extract_identifier_name(child)
            if name:
                vars_found.append(name)

    return vars_found


def _extract_compute_targets(stmt: ParseNode) -> list[str]:
    """Extract target variables from COMPUTE statement."""
    vars_found: list[str] = []

    # In COMPUTE X = expr, X is target (before =)
    found_eq = False
    for child in stmt.children:
        if child.text and "=" in child.text:
            found_eq = True
            continue

        # Before = - these are targets
        if not found_eq and child.type and "identifier" in child.type.lower():
            name = _extract_identifier_name(child)
            if name:
                vars_found.append(name)

    return vars_found


def _extract_compute_sources(stmt: ParseNode) -> list[str]:
    """Extract source variables from COMPUTE statement."""
    vars_found: list[str] = []

    # In COMPUTE X = A + B, A and B are sources (after =)
    found_eq = False
    for child in stmt.children:
        if child.text and "=" in child.text:
            found_eq = True
            continue

        # After = - these are sources
        if found_eq and child.type and "identifier" in child.type.lower():
            name = _extract_identifier_name(child)
            if name:
                vars_found.append(name)

    return vars_found


def _extract_all_identifiers(node: ParseNode) -> set[str]:
    """Extract all identifier names from a node."""
    identifiers: set[str] = set()

    id_nodes = _find_all_nodes(
        node, ["Identifier", "identifier", "QualifiedDataName", "qualifiedDataName"]
    )

    for id_node in id_nodes:
        name = _extract_identifier_name(id_node)
        if name:
            identifiers.add(name)

    return identifiers


def _extract_identifier_name(node: ParseNode) -> str | None:
    """Extract name from an identifier node."""
    if node.value:
        return str(node.value)
    if node.text:
        return node.text

    # Search children
    for child in node.children:
        name = _extract_identifier_name(child)
        if name:
            return name

    return None


def _extract_call_parameters(stmt: ParseNode) -> list[str]:
    """Extract parameters from CALL USING clause."""
    params: list[str] = []

    using_nodes = _find_all_nodes(stmt, ["CallUsingPhrase", "callUsingPhrase"])
    for using in using_nodes:
        ids = _extract_all_identifiers(using)
        params.extend(ids)

    return params


def serialize_dfg(dfg: DataFlowGraph) -> dict[str, Any]:
    """Serialize DFG to dictionary for JSON output."""
    return dfg.model_dump(mode="json")
