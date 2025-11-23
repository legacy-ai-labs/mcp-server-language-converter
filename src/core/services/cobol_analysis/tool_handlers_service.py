"""Registry of COBOL analysis tool handlers."""

import json
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from src.core.models.cobol_analysis_model import (
    ASTNode,
    BasicBlock,
    CFGEdge,
    CFGEdgeType,
    CFGNode,
    ControlFlowGraph,
    ControlFlowNode,
    DataFlowGraph,
    DataFlowNode,
    DFGEdge,
    DFGEdgeType,
    DFGNode,
    DivisionNode,
    DivisionType,
    EntryNode,
    ExitNode,
    ExpressionNode,
    LiteralNode,
    ParagraphNode,
    PDGEdge,
    PDGEdgeType,
    PDGNode,
    ProgramNode,
    SectionNode,
    SourceLocation,
    StatementNode,
    StatementType,
    VariableDefNode,
    VariableNode,
    VariableUseNode,
)
from src.core.services.cobol_analysis.ast_builder_service import build_ast
from src.core.services.cobol_analysis.cfg_builder_service import build_cfg
from src.core.services.cobol_analysis.cobol_parser_antlr_service import (
    ParseNode,
    parse_cobol,
    parse_cobol_file,
)
from src.core.services.cobol_analysis.dfg_builder_service import build_dfg
from src.core.services.cobol_analysis.pdg_builder_service import build_pdg


logger = logging.getLogger(__name__)


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


# ============================================================================
# Result persistence helper
# ============================================================================


def _save_tool_result(
    tool_name: str,
    result: dict[str, Any],
    source_identifier: str | None = None,
) -> Path | None:
    """Save tool execution result to tests/cobol_samples/result directory.

    Args:
        tool_name: Name of the tool (e.g., "parse_cobol", "build_cfg")
        result: Tool execution result dictionary
        source_identifier: Optional identifier for the source (e.g., program name, file path)

    Returns:
        Path to the saved file, or None if save failed
    """
    try:
        # Create result directory if it doesn't exist
        result_dir = Path("tests/cobol_samples/result")
        result_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        identifier = source_identifier or "unknown"
        # Sanitize identifier for filename
        identifier = "".join(c if c.isalnum() or c in "-_" else "_" for c in identifier)
        filename = f"{tool_name}_{identifier}_{timestamp}.json"
        filepath = result_dir / filename

        # Save result as JSON
        with filepath.open("w") as f:
            json.dump(result, f, indent=2, default=str)

        logger.info(f"Saved {tool_name} result to {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save {tool_name} result: {e}")
        return None


# ============================================================================
# Deserialization helpers for AST/CFG/DFG models
# ============================================================================


def _deserialize_source_location(location_dict: dict[str, Any] | None) -> SourceLocation | None:
    """Deserialize SourceLocation from dict."""
    if location_dict is None:
        return None
    return SourceLocation(
        line=location_dict.get("line", 0),
        column=location_dict.get("column"),
        file_path=location_dict.get("file_path"),
    )


def _deserialize_ast_node(node_dict: dict[str, Any]) -> ASTNode:
    """Deserialize AST node from dict."""
    if not isinstance(node_dict, dict):
        raise ValueError(f"Expected dict for AST node, got {type(node_dict).__name__}")

    node_type = node_dict.get("type", "")

    # Handle empty or missing type field
    if not node_type:
        logger.warning(
            f"AST node missing 'type' field. Node keys: {list(node_dict.keys())}, "
            f"Sample data: {str(node_dict)[:200]}"
        )
        raise ValueError(f"AST node missing 'type' field. Available keys: {list(node_dict.keys())}")

    location = _deserialize_source_location(node_dict.get("location"))

    if node_type == "ProgramNode":
        return ProgramNode(
            program_name=node_dict.get("program_name", ""),
            divisions=cast(
                list[DivisionNode],
                [_deserialize_ast_node(div) for div in node_dict.get("divisions", [])],
            ),
            location=location,
        )
    if node_type == "DivisionNode":
        division_type_str = node_dict.get("division_type", "IDENTIFICATION")
        division_type = (
            DivisionType(division_type_str)
            if division_type_str in [dt.value for dt in DivisionType]
            else DivisionType.IDENTIFICATION
        )
        return DivisionNode(
            division_type=division_type,
            sections=cast(
                list[SectionNode],
                [_deserialize_ast_node(sec) for sec in node_dict.get("sections", [])],
            ),
            location=location,
        )
    if node_type == "SectionNode":
        return SectionNode(
            section_name=node_dict.get("section_name"),
            paragraphs=cast(
                list[ParagraphNode],
                [_deserialize_ast_node(para) for para in node_dict.get("paragraphs", [])],
            ),
            location=location,
        )
    if node_type == "ParagraphNode":
        return ParagraphNode(
            paragraph_name=node_dict.get("paragraph_name", ""),
            statements=cast(
                list[StatementNode],
                [_deserialize_ast_node(stmt) for stmt in node_dict.get("statements", [])],
            ),
            location=location,
        )
    if node_type == "StatementNode":
        statement_type_str = node_dict.get("statement_type", "IF")
        statement_type = (
            StatementType(statement_type_str)
            if statement_type_str in [st.value for st in StatementType]
            else StatementType.IF
        )
        attrs: dict[str, Any] = {}
        for key, value in node_dict.get("attributes", {}).items():
            if isinstance(value, dict) and value.get("type") in [
                "ExpressionNode",
                "VariableNode",
                "LiteralNode",
                "StatementNode",
            ]:
                attrs[key] = _deserialize_ast_node(value)
            elif isinstance(value, list):
                attrs[key] = [
                    _deserialize_ast_node(item)
                    if isinstance(item, dict)
                    and item.get("type")
                    in ["StatementNode", "ExpressionNode", "VariableNode", "LiteralNode"]
                    else item
                    for item in value
                ]
            else:
                attrs[key] = value
        return StatementNode(
            statement_type=statement_type,
            attributes=attrs,
            location=location,
        )
    if node_type == "ExpressionNode":
        left = _deserialize_ast_node(left_dict) if (left_dict := node_dict.get("left")) else None
        right = (
            _deserialize_ast_node(right_dict) if (right_dict := node_dict.get("right")) else None
        )
        return ExpressionNode(
            operator=node_dict.get("operator"),
            left=left,
            right=right,
            value=node_dict.get("value"),
            location=location,
        )
    if node_type == "VariableNode":
        return VariableNode(
            variable_name=node_dict.get("variable_name", ""),
            pic_clause=node_dict.get("pic_clause"),
            level_number=node_dict.get("level_number"),
            location=location,
        )
    if node_type == "LiteralNode":
        return LiteralNode(
            value=node_dict.get("value", ""),
            literal_type=node_dict.get("literal_type", "STRING"),
            location=location,
        )
    # Fallback for unknown types
    raise ValueError(f"Unknown AST node type: {node_type}")


def _deserialize_cfg_node(node_dict: dict[str, Any]) -> CFGNode:
    """Deserialize CFG node from dict."""
    node_id = node_dict.get("node_id", "")
    label = node_dict.get("label", "")
    location = _deserialize_source_location(node_dict.get("location"))
    node_type = node_dict.get("node_type", "")

    if node_type == "EntryNode" or node_id == "entry":
        return EntryNode(node_id=node_id, location=location)
    if node_type == "ExitNode" or node_id == "exit":
        return ExitNode(node_id=node_id, location=location)
    if node_type == "BasicBlock":
        statements: list[StatementNode] = cast(
            list[StatementNode],
            [_deserialize_ast_node(stmt) for stmt in node_dict.get("statements", [])],
        )
        block = BasicBlock(node_id=node_id, label=label, location=location)
        block.statements = statements
        return block
    if node_type == "ControlFlowNode":
        condition_dict = node_dict.get("condition")
        condition_node = (
            _deserialize_ast_node(condition_dict)
            if condition_dict and isinstance(condition_dict, dict)
            else None
        )
        condition = condition_node if isinstance(condition_node, ExpressionNode) else None
        control_node = ControlFlowNode(
            node_id=node_id,
            label=label,
            location=location,
            control_type=node_dict.get("control_type", ""),
            condition=condition,
            target_paragraph=node_dict.get("target_paragraph"),
        )
        return control_node
    # Fallback to base CFGNode
    return CFGNode(node_id=node_id, label=label, location=location)


def _deserialize_cfg_edge(edge_dict: dict[str, Any], node_lookup: dict[str, CFGNode]) -> CFGEdge:
    """Deserialize CFG edge from dict."""
    source_id = edge_dict.get("source_id", "")
    target_id = edge_dict.get("target_id", "")
    edge_type_str = edge_dict.get("edge_type", "SEQUENTIAL")
    edge_type = (
        CFGEdgeType(edge_type_str)
        if edge_type_str in [et.value for et in CFGEdgeType]
        else CFGEdgeType.SEQUENTIAL
    )
    label = edge_dict.get("label", "")

    source = node_lookup.get(source_id)
    target = node_lookup.get(target_id)

    if source is None or target is None:
        raise ValueError(f"Missing node for edge: source_id={source_id}, target_id={target_id}")

    return CFGEdge(source=source, target=target, edge_type=edge_type, label=label)


def _deserialize_cfg(cfg_dict: dict[str, Any]) -> ControlFlowGraph:
    """Deserialize ControlFlowGraph from dict."""
    entry_node_dict = cfg_dict.get("entry_node", {})
    exit_node_dict = cfg_dict.get("exit_node", {})
    nodes_dict = cfg_dict.get("nodes", [])
    edges_dict = cfg_dict.get("edges", [])

    entry_node_raw = _deserialize_cfg_node(entry_node_dict)
    exit_node_raw = _deserialize_cfg_node(exit_node_dict)

    # Cast to specific types expected by ControlFlowGraph
    if not isinstance(entry_node_raw, EntryNode):
        raise ValueError(f"Expected EntryNode, got {type(entry_node_raw).__name__}")
    if not isinstance(exit_node_raw, ExitNode):
        raise ValueError(f"Expected ExitNode, got {type(exit_node_raw).__name__}")

    entry_node = entry_node_raw
    exit_node = exit_node_raw

    # Build node lookup dictionary
    node_lookup: dict[str, CFGNode] = {entry_node.node_id: entry_node, exit_node.node_id: exit_node}
    for node_dict in nodes_dict:
        node = _deserialize_cfg_node(node_dict)
        node_lookup[node.node_id] = node

    # Build graph
    cfg = ControlFlowGraph(entry_node=entry_node, exit_node=exit_node)
    cfg.add_node(entry_node)
    cfg.add_node(exit_node)

    # Add all nodes
    for node_dict in nodes_dict:
        node = _deserialize_cfg_node(node_dict)
        cfg.add_node(node)

    # Add all edges
    for edge_dict in edges_dict:
        edge = _deserialize_cfg_edge(edge_dict, node_lookup)
        cfg.add_edge(edge)

    return cfg


def _deserialize_dfg(dfg_dict: dict[str, Any]) -> DataFlowGraph:
    """Deserialize DataFlowGraph from dict.

    Note: This is a simplified deserialization that doesn't reconstruct
    full statement references. Use for PDG building where we only need
    the graph structure, not the full statement objects.
    """
    nodes_dict = dfg_dict.get("nodes", [])
    edges_dict = dfg_dict.get("edges", [])

    dfg = DataFlowGraph()

    # Build node lookup dictionary
    node_lookup: dict[str, DFGNode] = {}

    # Create all nodes
    for node_dict in nodes_dict:
        node_type = node_dict.get("node_type", "")
        node_id = node_dict.get("node_id", "")
        variable_name = node_dict.get("variable_name", "")
        location = _deserialize_source_location(node_dict.get("location"))

        node: DFGNode
        if node_type == "VariableDefNode":
            node = VariableDefNode(
                node_id=node_id,
                variable_name=variable_name,
                location=location,
            )
        elif node_type == "VariableUseNode":
            node = VariableUseNode(
                node_id=node_id,
                variable_name=variable_name,
                location=location,
                context=node_dict.get("context", ""),
            )
        elif node_type == "DataFlowNode":
            node = DataFlowNode(
                node_id=node_id,
                variable_name=variable_name,
                location=location,
                transformation_type=node_dict.get("transformation_type", ""),
            )
        else:
            # Generic DFGNode
            node = DFGNode(
                node_id=node_id,
                variable_name=variable_name,
                location=location,
            )

        dfg.add_node(node)
        node_lookup[node_id] = node

    # Create all edges
    for edge_dict in edges_dict:
        source_id = edge_dict.get("source_id", "")
        target_id = edge_dict.get("target_id", "")
        edge_type_str = edge_dict.get("edge_type", "DEF_USE")
        label = edge_dict.get("label", "")

        source = node_lookup.get(source_id)
        target = node_lookup.get(target_id)

        if source is None or target is None:
            logger.warning(f"Skipping DFG edge with missing nodes: {source_id} -> {target_id}")
            continue

        edge_type = DFGEdgeType(edge_type_str) if edge_type_str else DFGEdgeType.DEF_USE

        edge = DFGEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            label=label,
        )
        dfg.add_edge(edge)

    return dfg


def _deserialize_parse_node(node_dict: dict[str, Any]) -> ParseNode:
    """Deserialize ParseNode from dict.

    Args:
        node_dict: Dictionary representation of ParseNode

    Returns:
        ParseNode instance
    """
    node_type = node_dict.get("node_type", "")
    value = node_dict.get("value")
    line_number = node_dict.get("line_number")
    children = node_dict.get("children", [])

    # Recursively deserialize children
    deserialized_children = []
    for child in children:
        if isinstance(child, dict):
            deserialized_children.append(_deserialize_parse_node(child))
        else:
            deserialized_children.append(child)

    parse_node = ParseNode(node_type=node_type, children=deserialized_children, value=value)
    if line_number is not None:
        parse_node.line_number = line_number

    return parse_node


# ============================================================================
# Serialization helpers for AST/CFG/DFG models
# ============================================================================


def _serialize_source_location(location: SourceLocation | None) -> dict[str, Any] | None:
    """Serialize SourceLocation to dict."""
    if location is None:
        return None
    return {
        "line": location.line,
        "column": location.column,
        "file_path": location.file_path,
    }


def _serialize_ast_node(node: Any) -> dict[str, Any]:
    """Serialize AST node to dict."""
    # Dispatch to type-specific serializers
    if isinstance(node, ProgramNode):
        result = {
            "type": "ProgramNode",
            "program_name": node.program_name,
            "divisions": [_serialize_ast_node(div) for div in node.divisions],
            "location": _serialize_source_location(node.location),
        }
    elif isinstance(node, DivisionNode):
        result = {
            "type": "DivisionNode",
            "division_type": node.division_type.value,
            "sections": [_serialize_ast_node(sec) for sec in node.sections],
            "location": _serialize_source_location(node.location),
        }
    elif isinstance(node, SectionNode):
        result = {
            "type": "SectionNode",
            "section_name": node.section_name,
            "paragraphs": [_serialize_ast_node(para) for para in node.paragraphs],
            "location": _serialize_source_location(node.location),
        }
    elif isinstance(node, ParagraphNode):
        result = {
            "type": "ParagraphNode",
            "paragraph_name": node.paragraph_name,
            "statements": [_serialize_ast_node(stmt) for stmt in node.statements],
            "location": _serialize_source_location(node.location),
        }
    elif isinstance(node, StatementNode):
        attrs: dict[str, Any] = {}
        for key, value in node.attributes.items():
            if isinstance(value, ExpressionNode | VariableNode | LiteralNode):
                attrs[key] = _serialize_ast_node(value)
            elif isinstance(value, list):
                attrs[key] = [
                    _serialize_ast_node(item)
                    if isinstance(item, StatementNode | ExpressionNode | VariableNode | LiteralNode)
                    else item
                    for item in value
                ]
            else:
                attrs[key] = value
        result = {
            "type": "StatementNode",
            "statement_type": node.statement_type.value,
            "attributes": attrs,
            "location": _serialize_source_location(node.location),
        }
    elif isinstance(node, ExpressionNode):
        result = {
            "type": "ExpressionNode",
            "operator": node.operator,
            "left": _serialize_ast_node(node.left) if node.left else None,
            "right": _serialize_ast_node(node.right) if node.right else None,
            "value": node.value,
            "location": _serialize_source_location(node.location),
        }
    elif isinstance(node, VariableNode):
        result = {
            "type": "VariableNode",
            "variable_name": node.variable_name,
            "pic_clause": node.pic_clause,
            "level_number": cast(Any, node.level_number),
            "location": _serialize_source_location(node.location),
        }
    elif isinstance(node, LiteralNode):
        result = {
            "type": "LiteralNode",
            "value": cast(Any, node.value),
            "literal_type": node.literal_type,
            "location": _serialize_source_location(node.location),
        }
    else:
        result = {"type": str(type(node).__name__), "data": str(node)}
    return result


def _serialize_cfg_node(node: CFGNode) -> dict[str, Any]:
    """Serialize CFG node to dict."""
    base: dict[str, Any] = {
        "node_id": node.node_id,
        "label": node.label,
        "location": _serialize_source_location(node.location),
    }
    if isinstance(node, BasicBlock):
        base["statements"] = [_serialize_ast_node(stmt) for stmt in node.statements]
        base["node_type"] = "BasicBlock"
    elif isinstance(node, ControlFlowNode):
        base["control_type"] = node.control_type
        base["condition"] = _serialize_ast_node(node.condition) if node.condition else None
        base["target_paragraph"] = getattr(node, "target_paragraph", None)
        base["node_type"] = "ControlFlowNode"
    elif node.node_id == "entry":
        base["node_type"] = "EntryNode"
    elif node.node_id == "exit":
        base["node_type"] = "ExitNode"
    else:
        base["node_type"] = "CFGNode"
    return base


def _serialize_cfg_edge(edge: CFGEdge) -> dict[str, Any]:
    """Serialize CFG edge to dict."""
    return {
        "source_id": edge.source.node_id,
        "target_id": edge.target.node_id,
        "edge_type": edge.edge_type.value,
        "label": edge.label,
    }


def _serialize_dfg_node(node: DFGNode) -> dict[str, Any]:
    """Serialize DFG node to dict."""
    base = {
        "node_id": node.node_id,
        "variable_name": node.variable_name,
        "location": _serialize_source_location(node.location),
    }
    if hasattr(node, "statement"):
        statement = getattr(node, "statement", None)
        if statement:
            base["statement"] = _serialize_ast_node(statement)
    if hasattr(node, "context"):
        base["context"] = getattr(node, "context", "")
    if hasattr(node, "transformation_type"):
        base["transformation_type"] = getattr(node, "transformation_type", "")
    base["node_type"] = type(node).__name__
    return base


def _serialize_dfg_edge(edge: DFGEdge) -> dict[str, Any]:
    """Serialize DFG edge to dict."""
    return {
        "source_id": edge.source.node_id,
        "target_id": edge.target.node_id,
        "edge_type": edge.edge_type.value,
        "label": edge.label,
    }


def _serialize_pdg_node(node: PDGNode) -> dict[str, Any]:
    """Serialize PDG node to dict."""
    base = {
        "node_id": node.node_id,
        "label": node.label,
        "location": _serialize_source_location(node.location),
        "cfg_node_id": node.cfg_node_id,
    }
    if node.statement:
        base["statement"] = _serialize_ast_node(node.statement)
    return base


def _serialize_pdg_edge(edge: PDGEdge) -> dict[str, Any]:
    """Serialize PDG edge to dict."""
    return {
        "source_id": edge.source.node_id,
        "target_id": edge.target.node_id,
        "edge_type": edge.edge_type.value,
        "label": edge.label,
        "variable_name": edge.variable_name,
    }


def _serialize_parse_node(node: ParseNode) -> dict[str, Any]:
    """Serialize ParseNode to dict.

    Args:
        node: ParseNode instance to serialize

    Returns:
        Dictionary representation of ParseNode
    """
    return {
        "node_type": node.node_type,
        "value": node.value,
        "line_number": node.line_number,
        "children": [
            _serialize_parse_node(child) if isinstance(child, ParseNode) else child
            for child in node.children
        ],
    }


# ============================================================================
# COBOL Analysis Tool Handlers
# ============================================================================


def parse_cobol_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Parse COBOL source code into AST.

    Args:
        parameters: Handler parameters containing 'source_code' or 'file_path'

    Returns:
        Dictionary with AST representation
    """
    source_code = parameters.get("source_code")
    file_path = parameters.get("file_path")

    if not source_code and not file_path:
        return {
            "success": False,
            "error": "Either 'source_code' or 'file_path' must be provided",
        }

    try:
        if file_path:
            parsed_tree, comments = parse_cobol_file(file_path)
        else:
            if not isinstance(source_code, str):
                return {
                    "success": False,
                    "error": "'source_code' must be a string",
                }
            parsed_tree, comments = parse_cobol(source_code)

        ast = build_ast(parsed_tree, comments)
        ast_dict = _serialize_ast_node(ast)

        result = {
            "success": True,
            "ast": ast_dict,
            "program_name": ast.program_name,
        }

        # Save result to file
        saved_path = _save_tool_result("parse_cobol", result, ast.program_name)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to parse COBOL")
        return {
            "success": False,
            "error": str(e),
        }


def parse_cobol_raw_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Parse COBOL source code into raw ParseNode (parse tree).

    This tool returns the raw parse tree without building the AST.
    Use this when you want to inspect the parse tree or build the AST separately.

    Args:
        parameters: Handler parameters containing 'source_code' or 'file_path'

    Returns:
        Dictionary with ParseNode representation
    """
    source_code = parameters.get("source_code")
    file_path = parameters.get("file_path")

    if not source_code and not file_path:
        return {
            "success": False,
            "error": "Either 'source_code' or 'file_path' must be provided",
        }

    try:
        if file_path:
            parse_node, _ = parse_cobol_file(file_path)
        else:
            if not isinstance(source_code, str):
                return {
                    "success": False,
                    "error": "'source_code' must be a string",
                }
            parse_node, _ = parse_cobol(source_code)
        parse_tree_dict = _serialize_parse_node(parse_node)

        result = {
            "success": True,
            "parse_tree": parse_tree_dict,
            "node_type": parse_node.node_type,
        }

        # Save result to file
        identifier = Path(file_path).stem if file_path else "source_code"
        saved_path = _save_tool_result("parse_cobol_raw", result, identifier)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to parse COBOL")
        return {
            "success": False,
            "error": str(e),
        }


def build_ast_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build Abstract Syntax Tree (AST) from ParseNode.

    Args:
        parameters: Handler parameters containing 'parse_tree' (ParseNode as dict)

    Returns:
        Dictionary with AST representation
    """
    parse_tree_dict = parameters.get("parse_tree")
    if not parse_tree_dict:
        return {
            "success": False,
            "error": "Parse tree representation is required",
        }

    try:
        # Accept ParseNode directly or deserialize from dict
        if isinstance(parse_tree_dict, ParseNode):
            parse_tree = parse_tree_dict
        elif isinstance(parse_tree_dict, dict):
            parse_tree = _deserialize_parse_node(parse_tree_dict)
        else:
            return {
                "success": False,
                "error": "Parse tree must be a ParseNode instance or a serialized dictionary",
            }

        ast = build_ast(parse_tree)
        ast_dict = _serialize_ast_node(ast)

        result = {
            "success": True,
            "ast": ast_dict,
            "program_name": ast.program_name,
        }

        # Save result to file
        saved_path = _save_tool_result("build_ast", result, ast.program_name)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to build AST")
        return {
            "success": False,
            "error": str(e),
        }


def build_cfg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build Control Flow Graph (CFG) from AST.

    Args:
        parameters: Handler parameters containing 'ast' (AST representation as dict or ProgramNode)

    Returns:
        Dictionary with CFG representation
    """
    ast_dict = parameters.get("ast")
    if not ast_dict:
        return {
            "success": False,
            "error": "AST representation is required",
        }

    try:
        # Log what we received for debugging
        logger.debug(
            f"build_cfg_handler received ast_dict type={type(ast_dict).__name__}, "
            f"keys={list(ast_dict.keys()) if isinstance(ast_dict, dict) else 'N/A'}"
        )

        # Accept ProgramNode directly or deserialize from dict
        if isinstance(ast_dict, ProgramNode):
            ast = ast_dict
        elif isinstance(ast_dict, dict):
            ast_raw = _deserialize_ast_node(ast_dict)
            if not isinstance(ast_raw, ProgramNode):
                return {
                    "success": False,
                    "error": "AST must be a ProgramNode instance",
                }
            ast = ast_raw
        else:
            return {
                "success": False,
                "error": "AST must be a ProgramNode instance or a serialized dictionary",
            }

        cfg = build_cfg(ast)
        cfg_dict = {
            "entry_node": _serialize_cfg_node(cfg.entry_node),
            "exit_node": _serialize_cfg_node(cfg.exit_node),
            "nodes": [_serialize_cfg_node(node) for node in cfg.nodes],
            "edges": [_serialize_cfg_edge(edge) for edge in cfg.edges],
        }

        result = {
            "success": True,
            "cfg": cfg_dict,
            "node_count": len(cfg.nodes),
            "edge_count": len(cfg.edges),
        }

        # Save result to file
        saved_path = _save_tool_result("build_cfg", result, ast.program_name)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to build CFG")
        return {
            "success": False,
            "error": str(e),
        }


def build_dfg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build Data Flow Graph (DFG) from AST + CFG.

    Args:
        parameters: Handler parameters containing 'ast' and 'cfg' (as dicts or objects)

    Returns:
        Dictionary with DFG representation
    """
    ast_dict = parameters.get("ast")
    cfg_dict = parameters.get("cfg")

    if not ast_dict:
        return {
            "success": False,
            "error": "AST representation is required",
        }
    if not cfg_dict:
        return {
            "success": False,
            "error": "CFG representation is required",
        }

    try:
        # Accept ProgramNode directly or deserialize from dict
        if isinstance(ast_dict, ProgramNode):
            ast = ast_dict
        elif isinstance(ast_dict, dict):
            ast_raw = _deserialize_ast_node(ast_dict)
            if not isinstance(ast_raw, ProgramNode):
                return {
                    "success": False,
                    "error": "AST must be a ProgramNode instance",
                }
            ast = ast_raw
        else:
            return {
                "success": False,
                "error": "AST must be a ProgramNode instance or a serialized dictionary",
            }

        # Accept ControlFlowGraph directly or deserialize from dict
        if isinstance(cfg_dict, ControlFlowGraph):
            cfg = cfg_dict
        elif isinstance(cfg_dict, dict):
            cfg = _deserialize_cfg(cfg_dict)
        else:
            return {
                "success": False,
                "error": "CFG must be a ControlFlowGraph instance or a serialized dictionary",
            }

        dfg = build_dfg(ast, cfg)
        dfg_dict = {
            "nodes": [_serialize_dfg_node(node) for node in dfg.nodes],
            "edges": [_serialize_dfg_edge(edge) for edge in dfg.edges],
        }

        result = {
            "success": True,
            "dfg": dfg_dict,
            "node_count": len(dfg.nodes),
            "edge_count": len(dfg.edges),
        }

        # Save result to file
        saved_path = _save_tool_result("build_dfg", result, ast.program_name)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to build DFG")
        return {
            "success": False,
            "error": str(e),
        }


def _deserialize_ast_for_pdg(ast_dict: Any) -> tuple[bool, ProgramNode | None, str]:
    """Deserialize AST for PDG building.

    Returns:
        Tuple of (success, ast_or_none, error_message)
    """
    if not ast_dict:
        return False, None, "AST representation is required"
    if isinstance(ast_dict, ProgramNode):
        return True, ast_dict, ""
    if isinstance(ast_dict, dict):
        ast_raw = _deserialize_ast_node(ast_dict)
        if not isinstance(ast_raw, ProgramNode):
            return False, None, "AST must be a ProgramNode instance"
        return True, ast_raw, ""
    return False, None, "AST must be a ProgramNode instance or a serialized dictionary"


def _deserialize_cfg_for_pdg(cfg_dict: Any) -> tuple[bool, ControlFlowGraph | None, str]:
    """Deserialize CFG for PDG building.

    Returns:
        Tuple of (success, cfg_or_none, error_message)
    """
    if not cfg_dict:
        return False, None, "CFG representation is required"
    if isinstance(cfg_dict, ControlFlowGraph):
        return True, cfg_dict, ""
    if isinstance(cfg_dict, dict):
        return True, _deserialize_cfg(cfg_dict), ""
    return False, None, "CFG must be a ControlFlowGraph instance or a serialized dictionary"


def _deserialize_dfg_for_pdg(dfg_dict: Any) -> tuple[bool, DataFlowGraph | None, str]:
    """Deserialize DFG for PDG building.

    Returns:
        Tuple of (success, dfg_or_none, error_message)
    """
    if not dfg_dict:
        return False, None, "DFG representation is required"
    if isinstance(dfg_dict, DataFlowGraph):
        return True, dfg_dict, ""
    if isinstance(dfg_dict, dict):
        return True, _deserialize_dfg(dfg_dict), ""
    return False, None, "DFG must be a DataFlowGraph instance or a serialized dictionary"


def build_pdg_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Build Program Dependency Graph (PDG) from AST, CFG, and DFG.

    The PDG combines control dependencies (from CFG) and data dependencies
    (from DFG) into a unified graph showing all dependencies in the program.

    Args:
        parameters: Handler parameters containing 'ast', 'cfg', and 'dfg'
                   (as dicts or objects)

    Returns:
        Dictionary with PDG representation
    """
    ast_dict = parameters.get("ast")
    cfg_dict = parameters.get("cfg")
    dfg_dict = parameters.get("dfg")

    success, ast, error = _deserialize_ast_for_pdg(ast_dict)
    if not success:
        return {"success": False, "error": error}
    assert ast is not None  # Type narrowing for mypy  # nosec B101

    success, cfg, error = _deserialize_cfg_for_pdg(cfg_dict)
    if not success:
        return {"success": False, "error": error}
    assert cfg is not None  # Type narrowing for mypy  # nosec B101

    success, dfg, error = _deserialize_dfg_for_pdg(dfg_dict)
    if not success:
        return {"success": False, "error": error}
    assert dfg is not None  # Type narrowing for mypy  # nosec B101

    try:
        pdg = build_pdg(ast, cfg, dfg)
        pdg_dict = {
            "nodes": [_serialize_pdg_node(node) for node in pdg.nodes],
            "edges": [_serialize_pdg_edge(edge) for edge in pdg.edges],
        }

        # Count edge types
        control_edges = len([e for e in pdg.edges if e.edge_type == PDGEdgeType.CONTROL])
        data_edges = len([e for e in pdg.edges if e.edge_type == PDGEdgeType.DATA])

        result = {
            "success": True,
            "pdg": pdg_dict,
            "node_count": len(pdg.nodes),
            "edge_count": len(pdg.edges),
            "control_edge_count": control_edges,
            "data_edge_count": data_edges,
        }

        # Save result to file
        saved_path = _save_tool_result("build_pdg", result, ast.program_name)
        if saved_path:
            result["saved_to"] = str(saved_path)

        return result
    except Exception as e:
        logger.exception("Failed to build PDG")
        return {"success": False, "error": str(e)}


def _process_single_cobol_file(cobol_file: Path) -> dict[str, Any]:
    """Process a single COBOL file through all analysis stages.

    Args:
        cobol_file: Path to the COBOL file to process

    Returns:
        Dictionary with processing results for this file
    """
    file_result: dict[str, Any] = {
        "file_path": str(cobol_file),
        "success": False,
        "stages": {},
    }

    logger.info(f"Processing {cobol_file}")

    # Stage 1: Parse COBOL to AST
    parse_result = parse_cobol_handler({"file_path": str(cobol_file)})
    file_result["stages"]["parse"] = {
        "success": parse_result.get("success", False),
        "saved_to": parse_result.get("saved_to"),
    }

    if not parse_result.get("success"):
        file_result["error"] = f"Parse failed: {parse_result.get('error', 'Unknown error')}"
        return file_result

    ast = parse_result.get("ast")
    program_name = parse_result.get("program_name", "unknown")

    # Stage 2: Build CFG
    cfg_result = build_cfg_handler({"ast": ast})
    file_result["stages"]["cfg"] = {
        "success": cfg_result.get("success", False),
        "node_count": cfg_result.get("node_count"),
        "edge_count": cfg_result.get("edge_count"),
        "saved_to": cfg_result.get("saved_to"),
    }

    if not cfg_result.get("success"):
        file_result["error"] = f"CFG build failed: {cfg_result.get('error', 'Unknown error')}"
        return file_result

    cfg = cfg_result.get("cfg")

    # Stage 3: Build DFG
    dfg_result = build_dfg_handler({"ast": ast, "cfg": cfg})
    file_result["stages"]["dfg"] = {
        "success": dfg_result.get("success", False),
        "node_count": dfg_result.get("node_count"),
        "edge_count": dfg_result.get("edge_count"),
        "saved_to": dfg_result.get("saved_to"),
    }

    if not dfg_result.get("success"):
        file_result["error"] = f"DFG build failed: {dfg_result.get('error', 'Unknown error')}"
        return file_result

    dfg = dfg_result.get("dfg")

    # Stage 4: Build PDG
    pdg_result = build_pdg_handler({"ast": ast, "cfg": cfg, "dfg": dfg})
    file_result["stages"]["pdg"] = {
        "success": pdg_result.get("success", False),
        "node_count": pdg_result.get("node_count"),
        "edge_count": pdg_result.get("edge_count"),
        "control_edge_count": pdg_result.get("control_edge_count"),
        "data_edge_count": pdg_result.get("data_edge_count"),
        "saved_to": pdg_result.get("saved_to"),
    }

    if not pdg_result.get("success"):
        file_result["error"] = f"PDG build failed: {pdg_result.get('error', 'Unknown error')}"
        return file_result

    # All stages succeeded
    file_result["success"] = True
    file_result["program_name"] = program_name
    return file_result


def _find_cobol_files(root_path: Path, file_extensions: list[str]) -> list[Path]:
    """Find all COBOL files in directory and subdirectories.

    Args:
        root_path: Root directory to search
        file_extensions: List of file extensions to search for

    Returns:
        List of paths to COBOL files found
    """
    cobol_files: list[Path] = []
    for ext in file_extensions:
        cobol_files.extend(root_path.rglob(f"*{ext}"))
    return cobol_files


def _save_batch_summary(summary: dict[str, Any], output_path: Path) -> dict[str, Any]:
    """Save batch processing summary to JSON file.

    Args:
        summary: Summary dictionary to save
        output_path: Directory to save summary file in

    Returns:
        Updated summary with saved file path
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    summary_file = output_path / f"batch_summary_{timestamp}.json"
    with summary_file.open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    summary["summary_saved_to"] = str(summary_file)
    return summary


def batch_analyze_cobol_directory_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Batch analyze all COBOL files in a directory and its subdirectories.

    For each COBOL file found, this handler will:
    1. Parse the file to generate AST
    2. Build Control Flow Graph (CFG)
    3. Build Data Flow Graph (DFG)
    4. Build Program Dependency Graph (PDG)
    5. Save all results to JSON files

    Args:
        parameters: Handler parameters containing:
            - directory_path: Root directory to scan for COBOL files
            - file_extensions: Optional list of extensions (default: ['.cbl', '.cob', '.cobol'])
            - output_directory: Optional output dir for results (default: tests/cobol_samples/result)

    Returns:
        Dictionary with batch processing summary
    """
    directory_path = parameters.get("directory_path")
    file_extensions = parameters.get("file_extensions", [".cbl", ".cob", ".cobol"])
    output_directory = parameters.get("output_directory", "tests/cobol_samples/result")

    if not directory_path:
        return {"success": False, "error": "directory_path is required"}

    try:
        root_path = Path(directory_path)
        if not root_path.exists():
            return {"success": False, "error": f"Directory not found: {directory_path}"}

        if not root_path.is_dir():
            return {"success": False, "error": f"Path is not a directory: {directory_path}"}

        # Ensure output directory exists
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all COBOL files
        cobol_files = _find_cobol_files(root_path, file_extensions)

        if not cobol_files:
            return {
                "success": True,
                "message": f"No COBOL files found in {directory_path}",
                "files_processed": 0,
                "files_succeeded": 0,
                "files_failed": 0,
                "results": [],
            }

        logger.info(f"Found {len(cobol_files)} COBOL files to process")

        # Process each file
        results = []
        files_succeeded = 0
        files_failed = 0

        for cobol_file in cobol_files:
            try:
                file_result = _process_single_cobol_file(cobol_file)
                if file_result["success"]:
                    files_succeeded += 1
                else:
                    files_failed += 1
                results.append(file_result)
            except Exception as e:
                logger.exception(f"Failed to process {cobol_file}")
                results.append(
                    {
                        "file_path": str(cobol_file),
                        "success": False,
                        "error": str(e),
                        "stages": {},
                    }
                )
                files_failed += 1

        # Create and save summary
        summary = {
            "success": True,
            "directory": str(root_path),
            "files_found": len(cobol_files),
            "files_processed": len(results),
            "files_succeeded": files_succeeded,
            "files_failed": files_failed,
            "output_directory": str(output_path),
            "results": results,
        }

        summary = _save_batch_summary(summary, output_path)

        logger.info(
            f"Batch processing complete: {files_succeeded} succeeded, {files_failed} failed"
        )

        return summary

    except Exception as e:
        logger.exception("Batch processing failed")
        return {"success": False, "error": str(e)}


def analyze_program_system_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912
    """Analyze relationships across multiple COBOL programs to build a system-level graph.

    This tool performs comprehensive inter-program analysis to identify:
    - CALL relationships between programs
    - Shared COPYBOOK/COPY dependencies
    - Data flow through parameters (BY VALUE/REFERENCE)
    - Program entry/exit points
    - External file dependencies

    Args:
        parameters: Dictionary with:
            - directory_path: Root directory containing COBOL files
            - file_extensions: Optional list of extensions (default: ['.cbl', '.cob', '.cobol'])
            - include_inactive: Include commented-out relationships (default: False)
            - max_depth: Maximum directory depth to scan (default: None for unlimited)

    Returns:
        Dictionary containing:
            - programs: List of program metadata
            - call_graph: Call relationships between programs
            - copybook_usage: Copybook dependency matrix
            - data_flows: Parameter flow information
            - system_metrics: Overall system complexity metrics
    """
    try:
        # Extract parameters
        directory_path = parameters.get("directory_path")
        if not directory_path:
            return {
                "success": False,
                "error": "directory_path is required",
            }

        directory = Path(directory_path)
        if not directory.exists():
            return {
                "success": False,
                "error": f"Directory not found: {directory_path}",
            }

        file_extensions = parameters.get("file_extensions", [".cbl", ".cob", ".cobol"])
        # include_inactive = parameters.get("include_inactive", False)  # Reserved for future use
        max_depth = parameters.get("max_depth")

        # Data structures for system analysis
        programs = {}  # program_id -> program_info
        call_graph = defaultdict(list)  # caller -> list of callees
        copybook_usage = defaultdict(set)  # copybook -> set of programs using it
        data_flows = []  # List of parameter flow records
        external_files = defaultdict(set)  # file -> set of programs using it

        # Find all COBOL files
        pattern = "**/*" if max_depth is None else "*" * min(max_depth, 10) + "/*"
        cobol_files: list[Path] = []
        for ext in file_extensions:
            cobol_files.extend(directory.glob(f"{pattern}{ext}"))

        if not cobol_files:
            return {
                "success": True,
                "warning": f"No COBOL files found in {directory_path}",
                "programs": [],
                "call_graph": {},
                "copybook_usage": {},
                "data_flows": [],
                "system_metrics": {},
            }

        # Analyze each COBOL file
        for file_path in cobol_files:
            try:
                # Parse the file
                parse_result = parse_cobol_handler({"file_path": str(file_path)})

                if not parse_result.get("success"):
                    continue

                # ast = parse_result.get("ast")  # Reserved for future AST analysis
                metadata = parse_result.get("metadata", {})

                # Extract program ID
                program_id = metadata.get("program_info", {}).get("program_id")
                if not program_id:
                    # Try to extract from filename if not in metadata
                    program_id = file_path.stem.upper()

                # Store program information
                programs[program_id] = {
                    "file_path": str(file_path),
                    "program_id": program_id,
                    "size_metrics": metadata.get("size_metrics", {}),
                    "dependencies": [],
                    "callers": [],
                    "callees": [],
                    "copybooks": [],
                    "external_files": [],
                }

                # Extract dependencies from metadata
                dependencies = metadata.get("dependencies", {})

                # Process CALL statements
                for call in dependencies.get("calls", []):
                    called_program = call.get("target")
                    if called_program:
                        call_graph[program_id].append(called_program)
                        programs[program_id]["callees"].append(called_program)

                        # Track parameter flow
                        if call.get("parameters"):
                            data_flows.append(
                                {
                                    "from": program_id,
                                    "to": called_program,
                                    "parameters": call.get("parameters"),
                                    "type": "CALL",
                                }
                            )

                # Process COPY statements
                for copybook in dependencies.get("copybooks", []):
                    copybook_name = copybook.get("name")
                    if copybook_name:
                        copybook_usage[copybook_name].add(program_id)
                        programs[program_id]["copybooks"].append(copybook_name)

                # Process file references
                for file_ref in dependencies.get("files", []):
                    file_name = file_ref.get("name")
                    if file_name:
                        external_files[file_name].add(program_id)
                        programs[program_id]["external_files"].append(file_name)

            except Exception as e:
                # Log error but continue processing other files
                logger.warning(f"Error analyzing {file_path}: {e}")
                continue

        # Build reverse call graph (callers)
        for caller, callees in call_graph.items():
            for callee in callees:
                if callee in programs:
                    programs[callee]["callers"].append(caller)

        # Calculate system metrics
        total_programs = len(programs)
        total_calls = sum(len(callees) for callees in call_graph.values())
        total_copybooks = len(copybook_usage)

        # Identify isolated programs (no calls in or out)
        isolated_programs = [
            pid for pid, info in programs.items() if not info["callers"] and not info["callees"]
        ]

        # Identify entry points (called by no one)
        entry_points = [
            pid for pid, info in programs.items() if not info["callers"] and info["callees"]
        ]

        # Calculate complexity metrics
        max_fan_out = max((len(info["callees"]) for info in programs.values()), default=0)
        max_fan_in = max((len(info["callers"]) for info in programs.values()), default=0)

        system_metrics = {
            "total_programs": total_programs,
            "total_relationships": total_calls,
            "total_copybooks": total_copybooks,
            "total_external_files": len(external_files),
            "isolated_programs": len(isolated_programs),
            "entry_points": len(entry_points),
            "max_fan_out": max_fan_out,
            "max_fan_in": max_fan_in,
            "average_dependencies": total_calls / total_programs if total_programs > 0 else 0,
        }

        return {
            "success": True,
            "programs": programs,
            "call_graph": {k: list(v) for k, v in call_graph.items()},
            "copybook_usage": {k: list(v) for k, v in copybook_usage.items()},
            "data_flows": data_flows,
            "external_files": {k: list(v) for k, v in external_files.items()},
            "system_metrics": system_metrics,
            "entry_points": entry_points,
            "isolated_programs": isolated_programs,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"System analysis failed: {e!s}",
        }


def build_call_graph_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0915
    """Build a call graph showing CALL relationships between COBOL programs.

    This tool creates a directed graph of program calls, useful for:
    - Understanding program dependencies
    - Identifying entry points and dead code
    - Impact analysis for changes
    - Detecting circular dependencies

    Args:
        parameters: Dictionary with:
            - programs: Dictionary of program information from analyze_program_system
            - call_graph: Raw call relationships
            - output_format: Graph format (dict, dot, json, mermaid) (default: dict)
            - include_metrics: Include graph metrics (default: True)

    Returns:
        Dictionary containing:
            - nodes: List of program nodes with attributes
            - edges: List of call edges with attributes
            - metrics: Graph-level metrics (cycles, depth, components)
            - visualization: Graph in requested format
    """
    try:
        programs = parameters.get("programs", {})
        call_graph = parameters.get("call_graph", {})
        output_format = parameters.get("output_format", "dict")
        include_metrics = parameters.get("include_metrics", True)

        if not programs and not call_graph:
            return {
                "success": False,
                "error": "Either programs or call_graph must be provided",
            }

        # Build nodes list
        nodes = []
        for program_id, info in programs.items():
            node = {
                "id": program_id,
                "label": program_id,
                "type": "program",
                "metrics": {
                    "fan_in": len(info.get("callers", [])),
                    "fan_out": len(info.get("callees", [])),
                    "size": info.get("size_metrics", {}).get("total_lines", 0),
                },
                "attributes": {
                    "file_path": info.get("file_path"),
                    "is_entry_point": len(info.get("callers", [])) == 0,
                    "is_leaf": len(info.get("callees", [])) == 0,
                },
            }
            nodes.append(node)

        # Build edges list
        edges = []
        edge_id = 0
        for caller, callees in call_graph.items():
            for callee in callees:
                edge = {
                    "id": edge_id,
                    "source": caller,
                    "target": callee,
                    "type": "calls",
                    "weight": 1,  # Could be enhanced with call frequency if available
                }
                edges.append(edge)
                edge_id += 1

        # Calculate metrics if requested
        metrics = {}
        if include_metrics:
            # Detect cycles using DFS
            def find_cycles() -> list[list[str]]:
                cycles: list[list[str]] = []
                visited: set[str] = set()
                rec_stack: set[str] = set()

                def dfs(node: str, path: list[str]) -> bool:
                    visited.add(node)
                    rec_stack.add(node)
                    path.append(node)

                    for neighbor in call_graph.get(node, []):
                        if neighbor not in visited:
                            if dfs(neighbor, path.copy()):
                                return True
                        elif neighbor in rec_stack:
                            # Found a cycle
                            cycle_start = path.index(neighbor)
                            cycles.append([*path[cycle_start:], neighbor])

                    rec_stack.remove(node)
                    return False

                for node in programs:
                    if node not in visited:
                        dfs(node, [])

                return cycles

            cycles = find_cycles()

            # Find strongly connected components
            def find_components() -> list[list[str]]:
                # Tarjan's algorithm for SCCs
                index_counter = [0]
                stack: list[str] = []
                lowlinks: dict[str, int] = {}
                index: dict[str, int] = {}
                on_stack: dict[str, bool] = {}
                components: list[list[str]] = []

                def strongconnect(v: str) -> None:
                    index[v] = index_counter[0]
                    lowlinks[v] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(v)
                    on_stack[v] = True

                    for w in call_graph.get(v, []):
                        if w not in index:
                            strongconnect(w)
                            lowlinks[v] = min(lowlinks[v], lowlinks[w])
                        elif on_stack.get(w, False):
                            lowlinks[v] = min(lowlinks[v], index[w])

                    if lowlinks[v] == index[v]:
                        component = []
                        while True:
                            w = stack.pop()
                            on_stack[w] = False
                            component.append(w)
                            if w == v:
                                break
                        components.append(component)

                for v in programs:
                    if v not in index:
                        strongconnect(v)

                return components

            components = find_components()

            metrics = {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "has_cycles": len(cycles) > 0,
                "cycle_count": len(cycles),
                "cycles": cycles,
                "strongly_connected_components": len(components),
                "largest_component_size": max(len(c) for c in components) if components else 0,
                "density": len(edges) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0,
            }

        # Generate visualization in requested format
        visualization = None
        if output_format == "dot":
            # Generate Graphviz DOT format
            dot_lines = ["digraph CallGraph {"]
            dot_lines.append("  rankdir=TB;")
            dot_lines.append("  node [shape=box];")

            for node in nodes:
                attrs = []
                if node["attributes"]["is_entry_point"]:
                    attrs.append("style=filled,fillcolor=lightgreen")
                elif node["attributes"]["is_leaf"]:
                    attrs.append("style=filled,fillcolor=lightblue")

                attr_str = f'[{",".join(attrs)}]' if attrs else ""
                dot_lines.append(f'  "{node["id"]}" {attr_str};')

            for edge in edges:
                dot_lines.append(f'  "{edge["source"]}" -> "{edge["target"]}";')

            dot_lines.append("}")
            visualization = "\n".join(dot_lines)

        elif output_format == "mermaid":
            # Generate Mermaid diagram format
            mermaid_lines = ["graph TD"]

            for node in nodes:
                shape = "([" if node["attributes"]["is_entry_point"] else "["
                shape_end = "])" if node["attributes"]["is_entry_point"] else "]"
                mermaid_lines.append(f'  {node["id"]}{shape}{node["label"]}{shape_end}')

            for edge in edges:
                mermaid_lines.append(f'  {edge["source"]} --> {edge["target"]}')

            visualization = "\n".join(mermaid_lines)

        return {
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "metrics": metrics,
            "visualization": visualization,
            "format": output_format,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to build call graph: {e!s}",
        }


def analyze_copybook_usage_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Analyze COPYBOOK usage patterns across COBOL programs.

    This tool identifies:
    - Which programs use which copybooks
    - Shared copybook dependencies
    - Copybook impact analysis (which programs affected by copybook changes)
    - Unused copybooks
    - Most frequently used copybooks

    Args:
        parameters: Dictionary with:
            - copybook_usage: Dictionary of copybook -> programs mapping
            - programs: Optional program information dictionary
            - include_recommendations: Generate optimization recommendations (default: True)

    Returns:
        Dictionary containing:
            - copybooks: List of copybook analysis records
            - usage_matrix: Programs vs copybooks matrix
            - impact_analysis: Programs affected by each copybook
            - recommendations: Suggested optimizations
    """
    try:
        copybook_usage = parameters.get("copybook_usage", {})
        programs = parameters.get("programs", {})
        include_recommendations = parameters.get("include_recommendations", True)

        if not copybook_usage:
            return {
                "success": True,
                "warning": "No copybook usage data provided",
                "copybooks": [],
                "usage_matrix": {},
                "impact_analysis": {},
                "recommendations": [],
            }

        # Analyze each copybook
        copybooks = []
        for copybook_name, using_programs in copybook_usage.items():
            copybook_info = {
                "name": copybook_name,
                "usage_count": len(using_programs),
                "used_by": list(using_programs),
                "usage_percentage": len(using_programs) / len(programs) * 100 if programs else 0,
                "is_shared": len(using_programs) > 1,
                "is_heavily_used": len(using_programs) > 5,  # Threshold can be adjusted
            }
            copybooks.append(copybook_info)

        # Sort by usage count
        copybooks.sort(key=lambda x: x["usage_count"], reverse=True)

        # Build usage matrix (programs vs copybooks)
        usage_matrix: dict[str, list[str]] = {}
        all_programs = set()

        for copybook_name, using_programs in copybook_usage.items():
            all_programs.update(using_programs)
            for program in using_programs:
                if program not in usage_matrix:
                    usage_matrix[program] = []
                usage_matrix[program].append(copybook_name)

        # Impact analysis - reverse mapping for change impact
        impact_analysis = {}
        for copybook in copybooks:
            impact_analysis[copybook["name"]] = {
                "directly_affected": copybook["used_by"],
                "affected_count": copybook["usage_count"],
                "risk_level": "HIGH"
                if copybook["usage_count"] > 10
                else "MEDIUM"
                if copybook["usage_count"] > 5
                else "LOW",
                "change_complexity": "Complex"
                if copybook["is_heavily_used"]
                else "Moderate"
                if copybook["is_shared"]
                else "Simple",
            }

        # Generate recommendations if requested
        recommendations = []
        if include_recommendations:
            # Find potential consolidation candidates
            single_use_copybooks = [c for c in copybooks if c["usage_count"] == 1]
            if single_use_copybooks:
                recommendations.append(
                    {
                        "type": "CONSOLIDATION",
                        "priority": "LOW",
                        "description": (
                            f"Consider consolidating {len(single_use_copybooks)} single-use copybooks"
                        ),
                        "copybooks": [c["name"] for c in single_use_copybooks[:5]],  # Show first 5
                    }
                )

            # Find heavily shared copybooks that might need refactoring
            heavily_shared = [c for c in copybooks if c["usage_count"] > 10]
            if heavily_shared:
                recommendations.append(
                    {
                        "type": "REFACTORING",
                        "priority": "MEDIUM",
                        "description": f"{len(heavily_shared)} copybooks are used by >10 programs",
                        "copybooks": [c["name"] for c in heavily_shared],
                        "suggestion": "Consider breaking down into smaller, more focused copybooks",
                    }
                )

            # Find programs with too many copybook dependencies
            heavy_users = [
                (prog, copies)
                for prog, copies in usage_matrix.items()
                if len(copies) > 15  # Threshold can be adjusted
            ]
            if heavy_users:
                recommendations.append(
                    {
                        "type": "DEPENDENCY_REDUCTION",
                        "priority": "HIGH",
                        "description": f"{len(heavy_users)} programs have >15 copybook dependencies",
                        "programs": [prog for prog, _ in heavy_users[:5]],  # Show first 5
                        "suggestion": "Review for potential consolidation or modularization",
                    }
                )

        # Calculate summary statistics
        stats = {
            "total_copybooks": len(copybooks),
            "total_relationships": sum(c["usage_count"] for c in copybooks),
            "average_usage": (
                sum(c["usage_count"] for c in copybooks) / len(copybooks) if copybooks else 0
            ),
            "max_usage": max((c["usage_count"] for c in copybooks), default=0),
            "single_use_count": len(single_use_copybooks) if include_recommendations else 0,
            "shared_count": len([c for c in copybooks if c["is_shared"]]),
        }

        return {
            "success": True,
            "copybooks": copybooks,
            "usage_matrix": usage_matrix,
            "impact_analysis": impact_analysis,
            "recommendations": recommendations,
            "statistics": stats,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to analyze copybook usage: {e!s}",
        }


def analyze_data_flow_handler(parameters: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912, PLR0915
    """Analyze data flow through program parameters (BY VALUE/REFERENCE).

    This tool tracks how data flows between programs through CALL parameters,
    identifying:
    - Parameter passing patterns (BY VALUE vs BY REFERENCE)
    - Data dependencies between programs
    - Potential data integrity issues
    - Parameter type mismatches

    Args:
        parameters: Dictionary with:
            - data_flows: List of data flow records from analyze_program_system
            - programs: Optional program information
            - trace_variable: Optional specific variable to trace through the system

    Returns:
        Dictionary containing:
            - flows: Analyzed data flow records
            - chains: Data flow chains showing multi-hop flows
            - warnings: Potential issues detected
            - variable_usage: Usage patterns for traced variables
    """
    try:
        data_flows = parameters.get("data_flows", [])
        programs = parameters.get("programs", {})
        trace_variable = parameters.get("trace_variable")

        if not data_flows:
            return {
                "success": True,
                "warning": "No data flow information provided",
                "flows": [],
                "chains": [],
                "warnings": [],
                "variable_usage": {},
            }

        # Analyze each flow
        analyzed_flows = []
        parameter_types: dict[str, list[dict[str, Any]]] = {}  # Track parameter types across calls

        for flow in data_flows:
            analyzed = {
                "from": flow.get("from"),
                "to": flow.get("to"),
                "type": flow.get("type", "CALL"),
                "parameters": [],
            }

            # Analyze each parameter
            for param in flow.get("parameters", []):
                param_info = {
                    "name": param.get("name"),
                    "passing_mode": param.get("mode", "BY REFERENCE"),  # COBOL default
                    "data_type": param.get("type"),
                    "size": param.get("size"),
                    "is_modified": param.get("mode") == "BY REFERENCE",
                }
                analyzed["parameters"].append(param_info)

                # Track parameter types for mismatch detection
                param_key = f"{flow['to']}.{param.get('name')}"
                if param_key not in parameter_types:
                    parameter_types[param_key] = []
                parameter_types[param_key].append(
                    {
                        "caller": flow["from"],
                        "type": param.get("type"),
                        "size": param.get("size"),
                    }
                )

            analyzed_flows.append(analyzed)

        # Build data flow chains (trace multi-hop flows)
        chains = []
        if trace_variable:
            # Trace specific variable through the system
            def trace_flow(
                variable: str, start_program: str, visited: set[str] | None = None
            ) -> list[str]:
                if visited is None:
                    visited = set()

                if start_program in visited:
                    return []  # Avoid cycles

                visited.add(start_program)
                chain = [start_program]

                # Find outgoing flows from this program
                for flow in analyzed_flows:
                    if flow["from"] == start_program:
                        for param in flow["parameters"]:
                            if param["name"] == variable:
                                # Found flow of this variable
                                sub_chain = trace_flow(variable, flow["to"], visited.copy())
                                if sub_chain:
                                    return chain + sub_chain
                                else:
                                    return [*chain, flow["to"]]

                return chain

            # Trace from all entry points
            entry_points = [pid for pid, info in programs.items() if not info.get("callers")]

            for entry in entry_points:
                chain = trace_flow(trace_variable, entry)
                if len(chain) > 1:
                    chains.append(
                        {
                            "variable": trace_variable,
                            "start": entry,
                            "path": chain,
                            "length": len(chain),
                        }
                    )

        # Detect warnings and potential issues
        warnings: list[dict[str, Any]] = []

        # Check for parameter type mismatches
        for param_key, callers in parameter_types.items():
            if len(callers) > 1:
                types = {c["type"] for c in callers if c["type"]}
                sizes = {c["size"] for c in callers if c["size"]}

                if len(types) > 1 or len(sizes) > 1:
                    warnings.append(
                        {
                            "type": "PARAMETER_MISMATCH",
                            "severity": "HIGH",
                            "parameter": param_key,
                            "callers": [c["caller"] for c in callers],
                            "details": f"Inconsistent types: {types}, sizes: {sizes}",
                        }
                    )

        # Check for excessive parameter passing
        for flow in analyzed_flows:
            if len(flow["parameters"]) > 10:
                warnings.append(
                    {
                        "type": "EXCESSIVE_PARAMETERS",
                        "severity": "MEDIUM",
                        "from": flow["from"],
                        "to": flow["to"],
                        "parameter_count": len(flow["parameters"]),
                        "suggestion": "Consider using a data structure or reducing parameters",
                    }
                )

        # Analyze BY REFERENCE usage for potential side effects
        by_reference_flows = []
        for flow in analyzed_flows:
            ref_params = [p for p in flow["parameters"] if p["is_modified"]]
            if ref_params:
                by_reference_flows.append(
                    {
                        "from": flow["from"],
                        "to": flow["to"],
                        "modified_params": [p["name"] for p in ref_params],
                        "count": len(ref_params),
                    }
                )

                if len(ref_params) > 5:
                    warnings.append(
                        {
                            "type": "EXCESSIVE_SIDE_EFFECTS",
                            "severity": "MEDIUM",
                            "from": flow["from"],
                            "to": flow["to"],
                            "parameter_count": len(ref_params),
                            "suggestion": "Many BY REFERENCE parameters may cause side effects",
                        }
                    )

        # Build variable usage summary
        variable_usage: dict[str, dict[str, Any]] = {}
        for flow in analyzed_flows:
            for param in flow["parameters"]:
                var_name = param["name"]
                if var_name:
                    if var_name not in variable_usage:
                        variable_usage[var_name] = {
                            "occurrences": 0,
                            "programs": set(),
                            "by_value_count": 0,
                            "by_reference_count": 0,
                        }

                    var_info = variable_usage[var_name]
                    var_info["occurrences"] += 1
                    var_info["programs"].add(flow["from"])
                    var_info["programs"].add(flow["to"])

                    if param["passing_mode"] == "BY VALUE":
                        var_info["by_value_count"] += 1
                    else:
                        var_info["by_reference_count"] += 1

        # Convert sets to lists for JSON serialization
        for _var_name, var_info in variable_usage.items():
            var_info["programs"] = list(var_info["programs"])

        # Calculate statistics
        stats = {
            "total_flows": len(analyzed_flows),
            "total_parameters": sum(len(f["parameters"]) for f in analyzed_flows),
            "by_reference_flows": len(by_reference_flows),
            "unique_variables": len(variable_usage),
            "warnings_count": len(warnings),
        }

        return {
            "success": True,
            "flows": analyzed_flows,
            "chains": chains,
            "warnings": warnings,
            "variable_usage": variable_usage,
            "by_reference_summary": by_reference_flows,
            "statistics": stats,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to analyze data flow: {e!s}",
        }


# Registry mapping handler names to handler functions
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "parse_cobol_handler": parse_cobol_handler,
    "parse_cobol_raw_handler": parse_cobol_raw_handler,
    "build_ast_handler": build_ast_handler,
    "build_cfg_handler": build_cfg_handler,
    "build_dfg_handler": build_dfg_handler,
    "build_pdg_handler": build_pdg_handler,
    "batch_analyze_cobol_directory_handler": batch_analyze_cobol_directory_handler,
    "analyze_program_system_handler": analyze_program_system_handler,
    "build_call_graph_handler": build_call_graph_handler,
    "analyze_copybook_usage_handler": analyze_copybook_usage_handler,
    "analyze_data_flow_handler": analyze_data_flow_handler,
}


def get_handler(handler_name: str) -> ToolHandler | None:
    """Get a tool handler by name.

    Args:
        handler_name: Name of the handler

    Returns:
        Handler function or None if not found
    """
    return TOOL_HANDLERS.get(handler_name)


def list_handlers() -> list[str]:
    """List all available handler names.

    Returns:
        List of handler names
    """
    return list(TOOL_HANDLERS.keys())
