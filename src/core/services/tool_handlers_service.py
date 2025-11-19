"""Registry of predefined tool handlers."""

import logging
from collections.abc import Callable
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
from src.core.services.ast_builder_service import build_ast
from src.core.services.cfg_builder_service import build_cfg
from src.core.services.cobol_parser_antlr_service import ParseNode, parse_cobol, parse_cobol_file
from src.core.services.dfg_builder_service import build_dfg
from src.core.services.pdg_builder_service import build_pdg


logger = logging.getLogger(__name__)


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def echo_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Echo handler that returns the input text.

    Args:
        parameters: Handler parameters containing 'text' key

    Returns:
        Dictionary with echoed text
    """
    text = parameters.get("text", "")
    return {
        "success": True,
        "message": f"Echo: {text}",
        "original_text": text,
    }


def calculator_add_handler(parameters: dict[str, Any]) -> dict[str, Any]:
    """Add two numbers.

    Args:
        parameters: Handler parameters containing 'a' and 'b' keys

    Returns:
        Dictionary with the sum
    """
    a = parameters.get("a", 0)
    b = parameters.get("b", 0)

    try:
        result = float(a) + float(b)
        return {
            "success": True,
            "operation": "addition",
            "a": a,
            "b": b,
            "result": result,
        }
    except (ValueError, TypeError) as e:
        return {
            "success": False,
            "error": f"Invalid numbers provided: {e}",
        }


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
            if isinstance(value, (ExpressionNode, VariableNode, LiteralNode)):
                attrs[key] = _serialize_ast_node(value)
            elif isinstance(value, list):
                attrs[key] = [
                    _serialize_ast_node(item)
                    if isinstance(item, (StatementNode, ExpressionNode, VariableNode, LiteralNode))
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
    if hasattr(node, "statements"):
        base["statements"] = [_serialize_ast_node(stmt) for stmt in node.statements]
        base["node_type"] = "BasicBlock"
    elif hasattr(node, "control_type"):
        base["control_type"] = node.control_type
        base["condition"] = (
            _serialize_ast_node(node.condition)
            if hasattr(node, "condition") and node.condition
            else None
        )
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
    if hasattr(node, "statement") and node.statement:
        base["statement"] = _serialize_ast_node(node.statement)
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
            parsed_tree = parse_cobol_file(file_path)
        else:
            if not isinstance(source_code, str):
                return {
                    "success": False,
                    "error": "'source_code' must be a string",
                }
            parsed_tree = parse_cobol(source_code)

        ast = build_ast(parsed_tree)
        ast_dict = _serialize_ast_node(ast)

        return {
            "success": True,
            "ast": ast_dict,
            "program_name": ast.program_name,
        }
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
            parsed_tree = parse_cobol_file(file_path)
        else:
            if not isinstance(source_code, str):
                return {
                    "success": False,
                    "error": "'source_code' must be a string",
                }
            parsed_tree = parse_cobol(source_code)
        parse_tree_dict = _serialize_parse_node(parsed_tree)

        return {
            "success": True,
            "parse_tree": parse_tree_dict,
            "node_type": parsed_tree.node_type,
        }
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

        return {
            "success": True,
            "ast": ast_dict,
            "program_name": ast.program_name,
        }
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

        return {
            "success": True,
            "cfg": cfg_dict,
            "node_count": len(cfg.nodes),
            "edge_count": len(cfg.edges),
        }
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

        return {
            "success": True,
            "dfg": dfg_dict,
            "node_count": len(dfg.nodes),
            "edge_count": len(dfg.edges),
        }
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
    assert ast is not None  # Type narrowing for mypy

    success, cfg, error = _deserialize_cfg_for_pdg(cfg_dict)
    if not success:
        return {"success": False, "error": error}
    assert cfg is not None  # Type narrowing for mypy

    success, dfg, error = _deserialize_dfg_for_pdg(dfg_dict)
    if not success:
        return {"success": False, "error": error}
    assert dfg is not None  # Type narrowing for mypy

    try:
        pdg = build_pdg(ast, cfg, dfg)
        pdg_dict = {
            "nodes": [_serialize_pdg_node(node) for node in pdg.nodes],
            "edges": [_serialize_pdg_edge(edge) for edge in pdg.edges],
        }

        # Count edge types
        control_edges = len([e for e in pdg.edges if e.edge_type == PDGEdgeType.CONTROL])
        data_edges = len([e for e in pdg.edges if e.edge_type == PDGEdgeType.DATA])

        return {
            "success": True,
            "pdg": pdg_dict,
            "node_count": len(pdg.nodes),
            "edge_count": len(pdg.edges),
            "control_edge_count": control_edges,
            "data_edge_count": data_edges,
        }
    except Exception as e:
        logger.exception("Failed to build PDG")
        return {"success": False, "error": str(e)}


# Registry mapping handler names to handler functions
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "echo_handler": echo_handler,
    "calculator_add_handler": calculator_add_handler,
    "parse_cobol_handler": parse_cobol_handler,
    "parse_cobol_raw_handler": parse_cobol_raw_handler,
    "build_ast_handler": build_ast_handler,
    "build_cfg_handler": build_cfg_handler,
    "build_dfg_handler": build_dfg_handler,
    "build_pdg_handler": build_pdg_handler,
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
