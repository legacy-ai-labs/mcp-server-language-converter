"""Build Data Flow Graphs (DFG) from COBOL AST and CFG structures."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from src.core.models.cobol_analysis_model import (
    ControlFlowGraph,
    DataFlowGraph,
    DFGEdge,
    DFGEdgeType,
    DivisionNode,
    DivisionType,
    ExpressionNode,
    ParagraphNode,
    ProgramNode,
    SectionNode,
    StatementNode,
    StatementType,
    VariableDefNode,
    VariableNode,
    VariableUseNode,
)


class DFGBuilderError(ValueError):
    """Raised when a DFG cannot be generated from supplied structures."""


def build_dfg(ast: ProgramNode, cfg: ControlFlowGraph) -> DataFlowGraph:
    """Build a data flow graph from COBOL AST and CFG.

    Args:
        ast: Program AST produced by Step 3.
        cfg: Control Flow Graph produced by Step 4.

    Returns:
        DataFlowGraph describing variable definitions and uses.

    Raises:
        DFGBuilderError: If AST or CFG arguments are invalid.
    """
    if not isinstance(ast, ProgramNode):
        raise DFGBuilderError("AST root must be a ProgramNode.")
    if not isinstance(cfg, ControlFlowGraph):
        raise DFGBuilderError("CFG must be a ControlFlowGraph instance.")

    procedure_division = _find_procedure_division(ast.divisions)
    if procedure_division is None:
        raise DFGBuilderError("Procedure division is required to build DFG.")

    paragraphs = _collect_paragraphs(procedure_division.sections)
    if not paragraphs:
        raise DFGBuilderError("Procedure division must contain at least one paragraph.")

    graph = DataFlowGraph()
    definition_counters: defaultdict[str, int] = defaultdict(int)
    use_counters: defaultdict[str, int] = defaultdict(int)
    last_definitions: dict[str, VariableDefNode] = {}

    for paragraph in paragraphs:
        for statement in paragraph.statements:
            _process_statement(
                graph=graph,
                statement=statement,
                paragraph_name=paragraph.paragraph_name,
                definition_counters=definition_counters,
                use_counters=use_counters,
                last_definitions=last_definitions,
            )

    return graph


def _find_procedure_division(divisions: list[DivisionNode]) -> DivisionNode | None:
    for division in divisions:
        if division.division_type == DivisionType.PROCEDURE:
            return division
    return None


def _collect_paragraphs(sections: list[SectionNode]) -> list[ParagraphNode]:
    paragraphs: list[ParagraphNode] = []
    for section in sections:
        paragraphs.extend(section.paragraphs)
    return paragraphs


def _process_statement(
    graph: DataFlowGraph,
    statement: StatementNode,
    paragraph_name: str,
    definition_counters: defaultdict[str, int],
    use_counters: defaultdict[str, int],
    last_definitions: dict[str, VariableDefNode],
) -> None:
    uses = _extract_uses(statement, paragraph_name)
    use_nodes: list[VariableUseNode] = []

    for variable_name, context in uses:
        node_id = f"use_{variable_name}_{use_counters[variable_name]}"
        use_counters[variable_name] += 1
        use_node = VariableUseNode(
            node_id=node_id,
            variable_name=variable_name,
            statement=statement,
            context=context,
        )
        graph.add_node(use_node)
        last_definition = last_definitions.get(variable_name)
        if last_definition is not None:
            graph.add_edge(
                DFGEdge(
                    source=last_definition,
                    target=use_node,
                    edge_type=DFGEdgeType.DEF_USE,
                )
            )
        use_nodes.append(use_node)

    definitions = _extract_definitions(statement)

    for variable_name in definitions:
        node_id = f"def_{variable_name}_{definition_counters[variable_name]}"
        definition_counters[variable_name] += 1
        def_node = VariableDefNode(
            node_id=node_id,
            variable_name=variable_name,
            statement=statement,
        )
        graph.add_node(def_node)

        last_definition = last_definitions.get(variable_name)
        if last_definition is not None:
            graph.add_edge(
                DFGEdge(
                    source=last_definition,
                    target=def_node,
                    edge_type=DFGEdgeType.DEF_USE,
                )
            )

        for use_node in use_nodes:
            if use_node.variable_name == variable_name:
                graph.add_edge(
                    DFGEdge(
                        source=def_node,
                        target=use_node,
                        edge_type=DFGEdgeType.DEF_USE,
                    )
                )

        last_definitions[variable_name] = def_node

    _process_nested_statements(
        graph=graph,
        statement=statement,
        paragraph_name=paragraph_name,
        definition_counters=definition_counters,
        use_counters=use_counters,
        last_definitions=last_definitions,
    )


def _process_nested_statements(
    graph: DataFlowGraph,
    statement: StatementNode,
    paragraph_name: str,
    definition_counters: defaultdict[str, int],
    use_counters: defaultdict[str, int],
    last_definitions: dict[str, VariableDefNode],
) -> None:
    """Process nested statements, handling control flow correctly.

    For IF statements with both THEN and ELSE branches, we need special handling:
    - Both branches should see the same incoming definitions
    - Definitions from different branches should not flow into each other
    - Both branches' definitions should flow to code after the IF
    """
    # Special handling for IF statements with both branches
    if (
        statement.statement_type == StatementType.IF
        and "then_statements" in statement.attributes
        and "else_statements" in statement.attributes
    ):
        _process_if_statement(
            graph=graph,
            statement=statement,
            paragraph_name=paragraph_name,
            definition_counters=definition_counters,
            use_counters=use_counters,
            last_definitions=last_definitions,
        )
        return

    # Standard processing for other nested statements
    nested_keys = ("then_statements", "else_statements", "statements")
    for key in nested_keys:
        nested_value = statement.attributes.get(key)
        if not isinstance(nested_value, Iterable):
            continue
        for nested_statement in nested_value:
            if isinstance(nested_statement, StatementNode):
                _process_statement(
                    graph=graph,
                    statement=nested_statement,
                    paragraph_name=paragraph_name,
                    definition_counters=definition_counters,
                    use_counters=use_counters,
                    last_definitions=last_definitions,
                )


def _process_if_statement(
    graph: DataFlowGraph,
    statement: StatementNode,
    paragraph_name: str,
    definition_counters: defaultdict[str, int],
    use_counters: defaultdict[str, int],
    last_definitions: dict[str, VariableDefNode],
) -> None:
    """Process IF statement with both THEN and ELSE branches.

    Both branches see the same incoming definitions, and their definitions
    are merged for subsequent code.
    """
    # Save current state before processing branches
    incoming_definitions = dict(last_definitions)

    # Track definitions from each branch
    then_definitions: dict[str, list[VariableDefNode]] = {}
    else_definitions: dict[str, list[VariableDefNode]] = {}

    # Process THEN branch
    then_last_defs = dict(incoming_definitions)
    for nested_statement in statement.attributes["then_statements"]:
        if isinstance(nested_statement, StatementNode):
            _process_statement(
                graph=graph,
                statement=nested_statement,
                paragraph_name=paragraph_name,
                definition_counters=definition_counters,
                use_counters=use_counters,
                last_definitions=then_last_defs,
            )
    # Collect THEN branch definitions
    for var_name, def_node in then_last_defs.items():
        if var_name not in incoming_definitions or def_node != incoming_definitions[var_name]:
            if var_name not in then_definitions:
                then_definitions[var_name] = []
            then_definitions[var_name].append(def_node)

    # Process ELSE branch (start from incoming state, not THEN state)
    else_last_defs = dict(incoming_definitions)
    for nested_statement in statement.attributes["else_statements"]:
        if isinstance(nested_statement, StatementNode):
            _process_statement(
                graph=graph,
                statement=nested_statement,
                paragraph_name=paragraph_name,
                definition_counters=definition_counters,
                use_counters=use_counters,
                last_definitions=else_last_defs,
            )
    # Collect ELSE branch definitions
    for var_name, def_node in else_last_defs.items():
        if var_name not in incoming_definitions or def_node != incoming_definitions[var_name]:
            if var_name not in else_definitions:
                else_definitions[var_name] = []
            else_definitions[var_name].append(def_node)

    # Merge branch definitions for subsequent code
    # For each variable, use the definition from whichever branch(es) defined it
    for var_name in set(then_definitions.keys()) | set(else_definitions.keys()):
        # If both branches define it, use the ELSE branch definition
        # (arbitrary choice; in a full implementation we'd track all reaching definitions)
        if var_name in else_definitions:
            last_definitions[var_name] = else_definitions[var_name][-1]
        elif var_name in then_definitions:
            last_definitions[var_name] = then_definitions[var_name][-1]


def _extract_definitions(statement: StatementNode) -> list[str]:
    definitions: list[str] = []
    statement_type = statement.statement_type

    if statement_type in {StatementType.MOVE, StatementType.COMPUTE, StatementType.ADD}:
        target = statement.attributes.get("target")
        variable_name = _variable_name(target)
        if variable_name:
            definitions.append(variable_name)

    return definitions


def _extract_uses(statement: StatementNode, paragraph_name: str) -> list[tuple[str, str]]:
    uses: list[tuple[str, str]] = []
    attr = statement.attributes

    if statement.statement_type == StatementType.MOVE:
        source = attr.get("source")
        variable_name = _variable_name(source)
        if variable_name:
            uses.append((variable_name, f"{paragraph_name}:MOVE:source"))

    if statement.statement_type == StatementType.COMPUTE:
        expression = attr.get("expression")
        uses.extend(_collect_expression_variables(expression, paragraph_name, "COMPUTE"))

    if statement.statement_type == StatementType.IF:
        condition = attr.get("condition")
        uses.extend(_collect_expression_variables(condition, paragraph_name, "IF"))

    if statement.statement_type == StatementType.CALL:
        for parameter in attr.get("parameters", []):
            if isinstance(parameter, str):
                uses.append((parameter, f"{paragraph_name}:CALL:parameter"))

    return uses


def _collect_expression_variables(
    expression: ExpressionNode | None,
    paragraph_name: str,
    context: str,
) -> list[tuple[str, str]]:
    if expression is None:
        return []

    results: list[tuple[str, str]] = []

    if isinstance(expression.value, VariableNode):
        variable_name = _variable_name(expression.value)
        if variable_name:
            results.append((variable_name, f"{paragraph_name}:{context}:value"))
    elif isinstance(expression.value, str):
        results.append((expression.value, f"{paragraph_name}:{context}:value"))

    if expression.left is not None:
        if isinstance(expression.left, VariableNode):
            variable_name = _variable_name(expression.left)
            if variable_name:
                results.append((variable_name, f"{paragraph_name}:{context}:left"))
        elif isinstance(expression.left, ExpressionNode):
            results.extend(_collect_expression_variables(expression.left, paragraph_name, context))

    if expression.right is not None:
        if isinstance(expression.right, VariableNode):
            variable_name = _variable_name(expression.right)
            if variable_name:
                results.append((variable_name, f"{paragraph_name}:{context}:right"))
        elif isinstance(expression.right, ExpressionNode):
            results.extend(_collect_expression_variables(expression.right, paragraph_name, context))

    return results


def _variable_name(node: object | None) -> str | None:
    if isinstance(node, VariableNode) and node.variable_name:
        return node.variable_name
    return None
