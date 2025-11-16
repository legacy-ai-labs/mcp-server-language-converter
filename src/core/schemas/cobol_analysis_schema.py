"""Pydantic schemas for COBOL analysis tool validation."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Source Location Schema
# ============================================================================


class SourceLocationSchema(BaseModel):
    """Schema for source code location."""

    line: int = Field(..., description="Line number (1-indexed)")
    column: int | None = Field(None, description="Column number (1-indexed)")
    file_path: str | None = Field(None, description="Path to source file")


# ============================================================================
# AST Node Schemas
# ============================================================================


class ASTNodeSchema(BaseModel):
    """Base schema for AST nodes (polymorphic)."""

    type: str = Field(..., description="Node type (e.g., 'ProgramNode', 'StatementNode')")
    location: SourceLocationSchema | None = Field(None, description="Source location")


class ProgramNodeSchema(ASTNodeSchema):
    """Schema for ProgramNode."""

    type: str = Field(default="ProgramNode", description="Node type")
    program_name: str = Field(..., description="COBOL program name")
    divisions: list[dict[str, Any]] = Field(
        default_factory=list, description="List of division nodes"
    )


class DivisionNodeSchema(ASTNodeSchema):
    """Schema for DivisionNode."""

    type: str = Field(default="DivisionNode", description="Node type")
    division_type: str = Field(
        ..., description="Division type (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)"
    )
    sections: list[dict[str, Any]] = Field(
        default_factory=list, description="List of section nodes"
    )


class SectionNodeSchema(ASTNodeSchema):
    """Schema for SectionNode."""

    type: str = Field(default="SectionNode", description="Node type")
    section_name: str | None = Field(None, description="Section name")
    paragraphs: list[dict[str, Any]] = Field(
        default_factory=list, description="List of paragraph nodes"
    )


class ParagraphNodeSchema(ASTNodeSchema):
    """Schema for ParagraphNode."""

    type: str = Field(default="ParagraphNode", description="Node type")
    paragraph_name: str = Field(..., description="Paragraph name")
    statements: list[dict[str, Any]] = Field(
        default_factory=list, description="List of statement nodes"
    )


class StatementNodeSchema(ASTNodeSchema):
    """Schema for StatementNode."""

    type: str = Field(default="StatementNode", description="Node type")
    statement_type: str = Field(..., description="Statement type (IF, PERFORM, MOVE, etc.)")
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Statement-specific attributes"
    )


class ExpressionNodeSchema(ASTNodeSchema):
    """Schema for ExpressionNode."""

    type: str = Field(default="ExpressionNode", description="Node type")
    operator: str | None = Field(None, description="Expression operator")
    left: dict[str, Any] | None = Field(None, description="Left operand")
    right: dict[str, Any] | None = Field(None, description="Right operand")
    value: str | None = Field(None, description="Expression value")


class VariableNodeSchema(ASTNodeSchema):
    """Schema for VariableNode."""

    type: str = Field(default="VariableNode", description="Node type")
    variable_name: str = Field(..., description="Variable name")
    pic_clause: str | None = Field(None, description="PICTURE clause")
    level_number: int | None = Field(None, description="Level number")


class LiteralNodeSchema(ASTNodeSchema):
    """Schema for LiteralNode."""

    type: str = Field(default="LiteralNode", description="Node type")
    value: str = Field(..., description="Literal value")
    literal_type: str = Field(default="STRING", description="Literal type (STRING, NUMBER, etc.)")


# ============================================================================
# CFG Node Schemas
# ============================================================================


class CFGNodeSchema(BaseModel):
    """Schema for CFG nodes (polymorphic)."""

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(
        ..., description="Node type (BasicBlock, ControlFlowNode, EntryNode, ExitNode)"
    )
    location: SourceLocationSchema | None = Field(None, description="Source location")


class CFGEdgeSchema(BaseModel):
    """Schema for CFG edges."""

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    edge_type: str = Field(
        ..., description="Edge type (SequentialEdge, TrueEdge, FalseEdge, CallEdge, GotoEdge)"
    )
    label: str | None = Field(None, description="Edge label")


class CFGStructureSchema(BaseModel):
    """Schema for complete CFG structure."""

    entry_node: dict[str, Any] = Field(..., description="Entry node")
    exit_node: dict[str, Any] = Field(..., description="Exit node")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="List of CFG nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="List of CFG edges")


# ============================================================================
# DFG Node Schemas
# ============================================================================


class DFGNodeSchema(BaseModel):
    """Schema for DFG nodes."""

    node_id: str = Field(..., description="Unique node identifier")
    variable_name: str = Field(..., description="Variable name")
    node_type: str = Field(
        ..., description="Node type (VariableDefNode, VariableUseNode, DataFlowNode)"
    )
    location: SourceLocationSchema | None = Field(None, description="Source location")
    statement: dict[str, Any] | None = Field(None, description="Associated statement AST node")
    context: str | None = Field(None, description="Context information")
    transformation_type: str | None = Field(None, description="Transformation type")


class DFGEdgeSchema(BaseModel):
    """Schema for DFG edges."""

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    edge_type: str = Field(..., description="Edge type (DefUseEdge, UseDefEdge)")
    label: str | None = Field(None, description="Edge label")


class DFGStructureSchema(BaseModel):
    """Schema for complete DFG structure."""

    nodes: list[dict[str, Any]] = Field(default_factory=list, description="List of DFG nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="List of DFG edges")


# ============================================================================
# Request Schemas
# ============================================================================


class ParseCobolRequest(BaseModel):
    """Request schema for parse_cobol tool."""

    source_code: str | None = Field(None, description="COBOL source code as string")
    file_path: str | None = Field(None, description="Path to COBOL source file")

    @model_validator(mode="after")
    def validate_input(self) -> "ParseCobolRequest":
        """Validate that at least one input is provided."""
        if not self.source_code and not self.file_path:
            raise ValueError("Either 'source_code' or 'file_path' must be provided")
        return self


class BuildCfgRequest(BaseModel):
    """Request schema for build_cfg tool."""

    ast: dict[str, Any] = Field(..., description="AST representation (serialized ProgramNode)")


class BuildDfgRequest(BaseModel):
    """Request schema for build_dfg tool."""

    ast: dict[str, Any] = Field(..., description="AST representation (serialized ProgramNode)")
    cfg: dict[str, Any] = Field(..., description="CFG representation (serialized ControlFlowGraph)")


# ============================================================================
# Response Schemas
# ============================================================================


class ParseCobolResponse(BaseModel):
    """Response schema for parse_cobol tool."""

    success: bool = Field(..., description="Whether parsing succeeded")
    ast: dict[str, Any] | None = Field(None, description="AST representation (if successful)")
    program_name: str | None = Field(None, description="COBOL program name (if successful)")
    error: str | None = Field(None, description="Error message (if failed)")


class BuildCfgResponse(BaseModel):
    """Response schema for build_cfg tool."""

    success: bool = Field(..., description="Whether CFG construction succeeded")
    cfg: dict[str, Any] | None = Field(None, description="CFG representation (if successful)")
    node_count: int | None = Field(None, description="Number of CFG nodes (if successful)")
    edge_count: int | None = Field(None, description="Number of CFG edges (if successful)")
    error: str | None = Field(None, description="Error message (if failed)")


class BuildDfgResponse(BaseModel):
    """Response schema for build_dfg tool."""

    success: bool = Field(..., description="Whether DFG construction succeeded")
    dfg: dict[str, Any] | None = Field(None, description="DFG representation (if successful)")
    node_count: int | None = Field(None, description="Number of DFG nodes (if successful)")
    edge_count: int | None = Field(None, description="Number of DFG edges (if successful)")
    error: str | None = Field(None, description="Error message (if failed)")
