"""Data models for COBOL analysis (AST, CFG, DFG).

This module defines data structures for representing:
- AST (Abstract Syntax Tree): Syntactic structure of COBOL programs
- CFG (Control Flow Graph): Execution paths and control flow
- DFG (Data Flow Graph): Data dependencies and flow
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ============================================================================
# Source Location
# ============================================================================


@dataclass
class SourceLocation:
    """Represents a source code location."""

    line: int
    column: int | None = None
    file_path: str | None = None

    def __str__(self) -> str:
        """String representation of source location."""
        if self.file_path:
            return f"{self.file_path}:{self.line}"
        return f"line {self.line}"


# ============================================================================
# AST (Abstract Syntax Tree) Models
# ============================================================================


class DivisionType(str, Enum):
    """COBOL division types."""

    IDENTIFICATION = "IDENTIFICATION"
    ENVIRONMENT = "ENVIRONMENT"
    DATA = "DATA"
    PROCEDURE = "PROCEDURE"


class StatementType(str, Enum):
    """COBOL statement types."""

    IF = "IF"
    PERFORM = "PERFORM"
    CALL = "CALL"
    COMPUTE = "COMPUTE"
    MOVE = "MOVE"
    READ = "READ"
    WRITE = "WRITE"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    DISPLAY = "DISPLAY"
    ADD = "ADD"
    EVALUATE = "EVALUATE"
    EXIT = "EXIT"
    STOP = "STOP"
    GOTO = "GOTO"


@dataclass
class ASTNode:
    """Base class for AST nodes."""

    location: SourceLocation | None = None
    children: list["ASTNode"] = field(default_factory=list)

    def add_child(self, child: "ASTNode") -> None:
        """Add a child node."""
        self.children.append(child)


@dataclass
class ProgramNode(ASTNode):
    """Root node representing a COBOL program."""

    program_name: str = ""
    divisions: list["DivisionNode"] = field(default_factory=list)


@dataclass
class DivisionNode(ASTNode):
    """Represents a COBOL division."""

    division_type: DivisionType = DivisionType.IDENTIFICATION
    sections: list["SectionNode"] = field(default_factory=list)


@dataclass
class SectionNode(ASTNode):
    """Represents a section within a division."""

    section_name: str | None = None
    paragraphs: list["ParagraphNode"] = field(default_factory=list)


@dataclass
class ParagraphNode(ASTNode):
    """Represents a paragraph within a section."""

    paragraph_name: str = ""
    statements: list["StatementNode"] = field(default_factory=list)


@dataclass
class StatementNode(ASTNode):
    """Represents a COBOL statement."""

    statement_type: StatementType = StatementType.IF
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpressionNode(ASTNode):
    """Represents an expression (condition, calculation)."""

    operator: str | None = None
    left: "ASTNode | None" = None
    right: "ASTNode | None" = None
    value: Any = None


@dataclass
class VariableNode(ASTNode):
    """Represents a variable reference."""

    variable_name: str = ""
    pic_clause: str | None = None
    level_number: int | None = None


@dataclass
class LiteralNode(ASTNode):
    """Represents a literal value."""

    value: str | int | float = ""
    literal_type: str = "STRING"  # "STRING", "NUMBER", "ZERO", "SPACE"


# ============================================================================
# CFG (Control Flow Graph) Models
# ============================================================================


class CFGEdgeType(str, Enum):
    """Types of CFG edges."""

    SEQUENTIAL = "SEQUENTIAL"
    TRUE = "TRUE"
    FALSE = "FALSE"
    CALL = "CALL"
    RETURN = "RETURN"
    GOTO = "GOTO"
    LOOP = "LOOP"


@dataclass
class CFGNode:
    """Base class for CFG nodes."""

    node_id: str = ""
    location: SourceLocation | None = None
    label: str = ""

    def __hash__(self) -> int:
        """Make node hashable for use in sets/dicts."""
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        """Compare nodes by ID."""
        if not isinstance(other, CFGNode):
            return False
        return self.node_id == other.node_id


@dataclass
class BasicBlock(CFGNode):
    """Represents a basic block (sequence of statements with single entry/exit)."""

    statements: list[StatementNode] = field(default_factory=list)


@dataclass
class ControlFlowNode(CFGNode):
    """Represents a control flow construct (IF, PERFORM, GOTO)."""

    control_type: str = ""  # "IF", "PERFORM", "GOTO", "LOOP"
    condition: ExpressionNode | None = None
    target_paragraph: str | None = None  # For PERFORM/GOTO


@dataclass
class EntryNode(CFGNode):
    """Represents program entry point."""

    def __init__(self, node_id: str = "entry", location: SourceLocation | None = None):
        """Initialize entry node."""
        super().__init__(node_id=node_id, location=location, label="Entry")


@dataclass
class ExitNode(CFGNode):
    """Represents program exit point."""

    def __init__(self, node_id: str = "exit", location: SourceLocation | None = None):
        """Initialize exit node."""
        super().__init__(node_id=node_id, location=location, label="Exit")


@dataclass
class CFGEdge:
    """Represents an edge in the control flow graph."""

    source: CFGNode
    target: CFGNode
    edge_type: CFGEdgeType
    label: str = ""

    def __hash__(self) -> int:
        """Make edge hashable."""
        return hash((self.source.node_id, self.target.node_id, self.edge_type))

    def __eq__(self, other: object) -> bool:
        """Compare edges."""
        if not isinstance(other, CFGEdge):
            return False
        return (
            self.source == other.source
            and self.target == other.target
            and self.edge_type == other.edge_type
        )


@dataclass
class ControlFlowGraph:
    """Represents a complete control flow graph."""

    entry_node: EntryNode
    exit_node: ExitNode
    nodes: list[CFGNode] = field(default_factory=list)
    edges: list[CFGEdge] = field(default_factory=list)

    def add_node(self, node: CFGNode) -> None:
        """Add a node to the graph."""
        if node not in self.nodes:
            self.nodes.append(node)

    def add_edge(self, edge: CFGEdge) -> None:
        """Add an edge to the graph."""
        if edge not in self.edges:
            self.edges.append(edge)
            # Ensure source and target nodes are in the graph
            self.add_node(edge.source)
            self.add_node(edge.target)

    def get_successors(self, node: CFGNode) -> list[CFGNode]:
        """Get all successor nodes of a given node."""
        return [edge.target for edge in self.edges if edge.source == node]

    def get_predecessors(self, node: CFGNode) -> list[CFGNode]:
        """Get all predecessor nodes of a given node."""
        return [edge.source for edge in self.edges if edge.target == node]


# ============================================================================
# DFG (Data Flow Graph) Models
# ============================================================================


class DFGEdgeType(str, Enum):
    """Types of DFG edges."""

    DEF_USE = "DEF_USE"  # Definition to use
    USE_DEF = "USE_DEF"  # Use to definition (transformation)
    PARAMETER = "PARAMETER"  # Parameter passing


@dataclass
class DFGNode:
    """Base class for DFG nodes."""

    node_id: str = ""
    variable_name: str = ""
    location: SourceLocation | None = None

    def __hash__(self) -> int:
        """Make node hashable."""
        return hash((self.node_id, self.variable_name))

    def __eq__(self, other: object) -> bool:
        """Compare nodes."""
        if not isinstance(other, DFGNode):
            return False
        return self.node_id == other.node_id and self.variable_name == other.variable_name


@dataclass
class VariableDefNode(DFGNode):
    """Represents a variable definition (assignment)."""

    statement: StatementNode | None = None


@dataclass
class VariableUseNode(DFGNode):
    """Represents a variable use (read)."""

    statement: StatementNode | None = None
    context: str = ""  # e.g., "condition", "expression", "parameter"


@dataclass
class DataFlowNode(DFGNode):
    """Represents a data flow point (transformation)."""

    transformation_type: str = ""  # e.g., "COMPUTE", "MOVE"


@dataclass
class DFGEdge:
    """Represents an edge in the data flow graph."""

    source: DFGNode
    target: DFGNode
    edge_type: DFGEdgeType
    label: str = ""

    def __hash__(self) -> int:
        """Make edge hashable."""
        return hash((self.source.node_id, self.target.node_id, self.edge_type))

    def __eq__(self, other: object) -> bool:
        """Compare edges."""
        if not isinstance(other, DFGEdge):
            return False
        return (
            self.source == other.source
            and self.target == other.target
            and self.edge_type == other.edge_type
        )


@dataclass
class DataFlowGraph:
    """Represents a complete data flow graph."""

    nodes: list[DFGNode] = field(default_factory=list)
    edges: list[DFGEdge] = field(default_factory=list)

    def add_node(self, node: DFGNode) -> None:
        """Add a node to the graph."""
        if node not in self.nodes:
            self.nodes.append(node)

    def add_edge(self, edge: DFGEdge) -> None:
        """Add an edge to the graph."""
        if edge not in self.edges:
            self.edges.append(edge)
            # Ensure source and target nodes are in the graph
            self.add_node(edge.source)
            self.add_node(edge.target)

    def get_definitions(self, variable_name: str) -> list[VariableDefNode]:
        """Get all definition nodes for a variable."""
        return [
            node
            for node in self.nodes
            if isinstance(node, VariableDefNode) and node.variable_name == variable_name
        ]

    def get_uses(self, variable_name: str) -> list[VariableUseNode]:
        """Get all use nodes for a variable."""
        return [
            node
            for node in self.nodes
            if isinstance(node, VariableUseNode) and node.variable_name == variable_name
        ]

    def get_successors(self, node: DFGNode) -> list[DFGNode]:
        """Get all successor nodes of a given node."""
        return [edge.target for edge in self.edges if edge.source == node]

    def get_predecessors(self, node: DFGNode) -> list[DFGNode]:
        """Get all predecessor nodes of a given node."""
        return [edge.source for edge in self.edges if edge.target == node]
