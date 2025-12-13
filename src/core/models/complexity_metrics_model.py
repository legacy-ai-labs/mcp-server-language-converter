"""Complexity metrics model for COBOL analysis.

This module defines the ComplexityMetrics model that captures various complexity
measurements for COBOL programs. The model supports progressive population as
different analysis structures (AST, ASG, CFG, DFG) are built.

The complexity rating helps agents determine if deeper analysis is needed:
- LOW: Simple program, AST analysis sufficient
- MEDIUM: Moderate complexity, ASG recommended
- HIGH: Complex program, CFG analysis recommended
- VERY_HIGH: Very complex, full CFG/DFG analysis recommended
"""

from enum import Enum

from pydantic import BaseModel, Field


class ComplexityRating(str, Enum):
    """Complexity rating levels for COBOL programs."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class AnalysisLevel(str, Enum):
    """Analysis level indicating which structures have been used."""

    PARSING = "parsing"
    AST = "ast"
    ASG = "asg"
    CFG = "cfg"
    DFG = "dfg"


class LineMetrics(BaseModel):
    """Line-based metrics from source parsing."""

    total_lines: int = Field(default=0, description="Total lines in source file")
    code_lines: int = Field(default=0, description="Lines containing executable code")
    comment_lines: int = Field(default=0, description="Lines containing comments")
    blank_lines: int = Field(default=0, description="Empty lines")
    comment_ratio: float = Field(default=0.0, description="Ratio of comment lines to code lines")


class StructuralMetrics(BaseModel):
    """Structural metrics from AST analysis."""

    division_count: int = Field(default=0, description="Number of divisions")
    section_count: int = Field(default=0, description="Number of sections")
    paragraph_count: int = Field(default=0, description="Number of paragraphs")
    statement_count: int = Field(default=0, description="Total executable statements")
    data_item_count: int = Field(default=0, description="Number of data items defined")
    level_88_count: int = Field(default=0, description="Number of level 88 conditions")
    copybook_count: int = Field(default=0, description="Number of COPY statements")


class ControlFlowMetrics(BaseModel):
    """Control flow metrics from AST/CFG analysis."""

    if_count: int = Field(default=0, description="Number of IF statements")
    evaluate_count: int = Field(default=0, description="Number of EVALUATE statements")
    perform_count: int = Field(default=0, description="Number of PERFORM statements")
    goto_count: int = Field(default=0, description="Number of GO TO statements (bad practice)")
    alter_count: int = Field(default=0, description="Number of ALTER statements (very bad)")
    call_count: int = Field(default=0, description="Number of CALL statements")
    max_nesting_depth: int = Field(default=0, description="Maximum control structure nesting")
    cyclomatic_complexity: int = Field(
        default=1, description="Cyclomatic complexity (approximated from AST)"
    )
    cyclomatic_complexity_accurate: int | None = Field(
        default=None, description="Accurate cyclomatic complexity (from CFG)"
    )


class DataMetrics(BaseModel):
    """Data-related metrics from AST/ASG analysis."""

    working_storage_items: int = Field(default=0, description="Items in WORKING-STORAGE")
    linkage_items: int = Field(default=0, description="Items in LINKAGE SECTION")
    file_section_items: int = Field(default=0, description="Items in FILE SECTION")
    max_data_level: int = Field(default=0, description="Maximum data level depth")
    redefines_count: int = Field(default=0, description="Number of REDEFINES clauses")
    occurs_count: int = Field(default=0, description="Number of OCCURS clauses (arrays)")
    picture_clauses: int = Field(default=0, description="Number of PICTURE clauses")


class DependencyMetrics(BaseModel):
    """Dependency metrics from ASG analysis."""

    external_calls: list[str] = Field(default_factory=list, description="External program calls")
    called_by: list[str] = Field(default_factory=list, description="Programs that call this one")
    copybooks_used: list[str] = Field(default_factory=list, description="Copybooks referenced")
    files_accessed: list[str] = Field(default_factory=list, description="Files accessed")
    fan_in: int = Field(default=0, description="Number of callers")
    fan_out: int = Field(default=0, description="Number of callees")


class CFGMetrics(BaseModel):
    """Control Flow Graph metrics (populated when CFG is built)."""

    node_count: int = Field(default=0, description="Number of CFG nodes")
    edge_count: int = Field(default=0, description="Number of CFG edges")
    unreachable_paragraphs: list[str] = Field(
        default_factory=list, description="Paragraphs that are never executed"
    )
    infinite_loop_risk: list[str] = Field(
        default_factory=list, description="Potential infinite loops detected"
    )
    entry_points: list[str] = Field(default_factory=list, description="Entry points to the program")
    exit_points: list[str] = Field(default_factory=list, description="Exit points from the program")


class DFGMetrics(BaseModel):
    """Data Flow Graph metrics (populated when DFG is built)."""

    node_count: int = Field(default=0, description="Number of DFG nodes")
    edge_count: int = Field(default=0, description="Number of DFG edges")
    dead_variables: list[str] = Field(
        default_factory=list, description="Variables assigned but never read"
    )
    uninitialized_reads: list[str] = Field(
        default_factory=list, description="Variables read before assignment"
    )
    data_dependencies: int = Field(default=0, description="Number of data dependencies")


class ASGMetrics(BaseModel):
    """Abstract Semantic Graph metrics (populated when ASG is built)."""

    symbol_count: int = Field(default=0, description="Total symbols in symbol table")
    data_item_count: int = Field(default=0, description="Number of data items (variables)")
    paragraph_count: int = Field(default=0, description="Number of paragraphs defined")
    section_count: int = Field(default=0, description="Number of sections defined")
    resolved_references: int = Field(default=0, description="References successfully resolved")
    unresolved_references: int = Field(
        default=0, description="References that could not be resolved"
    )
    external_calls: list[str] = Field(
        default_factory=list, description="External program calls (CALL statements)"
    )
    internal_calls: list[str] = Field(
        default_factory=list, description="Internal procedure calls (PERFORM targets)"
    )
    copybooks_used: list[str] = Field(
        default_factory=list, description="Copybooks referenced via COPY statements"
    )
    files_defined: list[str] = Field(
        default_factory=list, description="Files defined in FILE SECTION"
    )
    entry_points: list[str] = Field(default_factory=list, description="Program entry points")
    ambiguous_references: list[str] = Field(
        default_factory=list, description="References with multiple candidates"
    )


class QualityIndicators(BaseModel):
    """Code quality indicators and warnings."""

    has_goto: bool = Field(default=False, description="Contains GO TO statements")
    has_alter: bool = Field(default=False, description="Contains ALTER statements")
    has_dead_code: bool = Field(default=False, description="Contains unreachable code")
    has_dead_variables: bool = Field(default=False, description="Contains unused variables")
    excessive_nesting: bool = Field(default=False, description="Nesting depth > 5")
    excessive_complexity: bool = Field(default=False, description="Cyclomatic complexity > 20")
    warnings: list[str] = Field(default_factory=list, description="Quality warnings")
    recommendations: list[str] = Field(default_factory=list, description="Improvement suggestions")


class ComplexityMetrics(BaseModel):
    """Complete complexity metrics for a COBOL program.

    This model aggregates all complexity measurements and can be progressively
    populated as different analysis structures are built:

    1. Parsing → LineMetrics
    2. AST → StructuralMetrics, ControlFlowMetrics (approx), DataMetrics
    3. ASG → DependencyMetrics (enhanced)
    4. CFG → CFGMetrics, ControlFlowMetrics.cyclomatic_complexity_accurate
    5. DFG → DFGMetrics

    The complexity_rating helps agents decide if deeper analysis is needed.
    """

    # Identification
    program_name: str | None = Field(default=None, description="Program identifier")
    source_file: str | None = Field(default=None, description="Source file path")
    analysis_level: AnalysisLevel = Field(
        default=AnalysisLevel.AST, description="Deepest analysis level completed"
    )

    # Metric groups
    line_metrics: LineMetrics = Field(default_factory=LineMetrics)
    structural_metrics: StructuralMetrics = Field(default_factory=StructuralMetrics)
    control_flow_metrics: ControlFlowMetrics = Field(default_factory=ControlFlowMetrics)
    data_metrics: DataMetrics = Field(default_factory=DataMetrics)
    dependency_metrics: DependencyMetrics = Field(default_factory=DependencyMetrics)
    cfg_metrics: CFGMetrics | None = Field(default=None, description="CFG metrics if built")
    dfg_metrics: DFGMetrics | None = Field(default=None, description="DFG metrics if built")
    asg_metrics: ASGMetrics | None = Field(default=None, description="ASG metrics if built")
    quality_indicators: QualityIndicators = Field(default_factory=QualityIndicators)

    # Overall assessment
    complexity_rating: ComplexityRating = Field(
        default=ComplexityRating.LOW, description="Overall complexity rating"
    )
    complexity_score: int = Field(default=0, description="Numeric complexity score (0-100)")

    # Recommendations for agent
    recommended_analysis: list[str] = Field(
        default_factory=list,
        description="Recommended additional analyses based on complexity",
    )

    def compute_complexity_rating(self) -> None:  # noqa: PLR0912
        """Compute overall complexity rating based on metrics.

        This method should be called after populating metrics to update
        the complexity_rating and complexity_score fields.
        """
        score = 0

        # Line-based scoring (max 15 points)
        if self.line_metrics.total_lines > 5000:
            score += 15
        elif self.line_metrics.total_lines > 2000:
            score += 10
        elif self.line_metrics.total_lines > 500:
            score += 5

        # Structural scoring (max 20 points)
        if self.structural_metrics.paragraph_count > 100:
            score += 10
        elif self.structural_metrics.paragraph_count > 50:
            score += 5
        if self.structural_metrics.statement_count > 1000:
            score += 10
        elif self.structural_metrics.statement_count > 500:
            score += 5

        # Control flow scoring (max 35 points)
        cc = (
            self.control_flow_metrics.cyclomatic_complexity_accurate
            or self.control_flow_metrics.cyclomatic_complexity
        )
        if cc > 50:
            score += 20
        elif cc > 20:
            score += 15
        elif cc > 10:
            score += 10
        elif cc > 5:
            score += 5

        if self.control_flow_metrics.goto_count > 0:
            score += 10
        if self.control_flow_metrics.alter_count > 0:
            score += 15
        if self.control_flow_metrics.max_nesting_depth > 5:
            score += 5

        # Data scoring (max 15 points)
        total_data = self.data_metrics.working_storage_items + self.data_metrics.linkage_items
        if total_data > 500:
            score += 10
        elif total_data > 200:
            score += 5
        if self.data_metrics.redefines_count > 20:
            score += 5

        # Dependency scoring (max 15 points)
        if self.dependency_metrics.fan_out > 20:
            score += 10
        elif self.dependency_metrics.fan_out > 10:
            score += 5
        if len(self.dependency_metrics.copybooks_used) > 20:
            score += 5

        self.complexity_score = min(score, 100)

        # Determine rating
        if score >= 70:
            self.complexity_rating = ComplexityRating.VERY_HIGH
        elif score >= 45:
            self.complexity_rating = ComplexityRating.HIGH
        elif score >= 25:
            self.complexity_rating = ComplexityRating.MEDIUM
        else:
            self.complexity_rating = ComplexityRating.LOW

        # Update quality indicators
        self.quality_indicators.has_goto = self.control_flow_metrics.goto_count > 0
        self.quality_indicators.has_alter = self.control_flow_metrics.alter_count > 0
        self.quality_indicators.excessive_nesting = self.control_flow_metrics.max_nesting_depth > 5
        self.quality_indicators.excessive_complexity = cc > 20

        # Generate recommendations for agent
        self._generate_recommendations()

    def _generate_recommendations(self) -> None:
        """Generate recommendations based on complexity analysis."""
        self.recommended_analysis = []
        self.quality_indicators.warnings = []
        self.quality_indicators.recommendations = []

        # Recommend deeper analysis based on complexity
        # ASG recommended for MEDIUM+ (semantic analysis, cross-references)
        is_medium_or_higher = self.complexity_rating in (
            ComplexityRating.MEDIUM,
            ComplexityRating.HIGH,
            ComplexityRating.VERY_HIGH,
        )
        if is_medium_or_higher and self.asg_metrics is None:
            self.recommended_analysis.append("build_asg")

        # CFG/DFG recommended for HIGH+ (control/data flow analysis)
        if self.complexity_rating in (ComplexityRating.HIGH, ComplexityRating.VERY_HIGH):
            if self.cfg_metrics is None:
                self.recommended_analysis.append("build_cfg")
            if self.dfg_metrics is None:
                self.recommended_analysis.append("build_dfg")

        # Add warnings
        if self.control_flow_metrics.goto_count > 0:
            self.quality_indicators.warnings.append(
                f"Contains {self.control_flow_metrics.goto_count} GO TO statements"
            )
            self.quality_indicators.recommendations.append(
                "Refactor GO TO statements to structured control flow"
            )

        if self.control_flow_metrics.alter_count > 0:
            self.quality_indicators.warnings.append(
                f"Contains {self.control_flow_metrics.alter_count} ALTER statements (critical)"
            )
            self.quality_indicators.recommendations.append(
                "ALTER statements make code extremely difficult to maintain - prioritize removal"
            )

        if self.quality_indicators.excessive_nesting:
            self.quality_indicators.warnings.append(
                f"Excessive nesting depth: {self.control_flow_metrics.max_nesting_depth}"
            )
            self.quality_indicators.recommendations.append(
                "Extract deeply nested logic into separate paragraphs"
            )

        cc = (
            self.control_flow_metrics.cyclomatic_complexity_accurate
            or self.control_flow_metrics.cyclomatic_complexity
        )
        if cc > 20:
            self.quality_indicators.warnings.append(f"High cyclomatic complexity: {cc}")
            self.quality_indicators.recommendations.append(
                "Consider breaking program into smaller, more focused modules"
            )

        if self.cfg_metrics and self.cfg_metrics.unreachable_paragraphs:
            self.quality_indicators.has_dead_code = True
            self.quality_indicators.warnings.append(
                f"Unreachable code: {len(self.cfg_metrics.unreachable_paragraphs)} paragraphs"
            )

        if self.dfg_metrics and self.dfg_metrics.dead_variables:
            self.quality_indicators.has_dead_variables = True
            self.quality_indicators.warnings.append(
                f"Dead variables: {len(self.dfg_metrics.dead_variables)} variables"
            )
