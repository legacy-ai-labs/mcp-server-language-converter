"""
ASG Builder Service - Builds Abstract Semantic Graph from ANTLR parse tree.

This service creates a full ASG using the cobol_asg_model.py Pydantic models from
the ANTLR parse tree. Pure Python implementation.

The ASG captures:
- Program structure with resolved references
- Data definitions with all clause types (34 clause types)
- Cross-references (who uses each data item)
- Procedure statements with full details
- CALL/PERFORM statement targets and parameters
- Copybook usage tracking (with COPY/REPLACE support via preprocessor)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from src.core.services.cobol_analysis.cobol_preprocessor_service import (
        PreprocessedSource,
    )

from src.core.models.cobol_asg_model import (
    BlankWhenZeroClause,
    CallGivingPhrase,
    CallParameter,
    CallStatement,
    CallType,
    CallUsingPhrase,
    CompilationUnit,
    ComputeStatement,
    DataDescriptionEntry,
    DataDescriptionEntryCall,
    DataDescriptionEntryType,
    DataDivision,
    EnvironmentDivision,
    EvaluateStatement,
    EvaluateWhen,
    ExternalClause,
    FileControlEntry,
    FileDescriptionEntry,
    FileOrganization,
    FileSection,
    GlobalClause,
    IdentificationDivision,
    IfStatement,
    InputOutputSection,
    JustifiedClause,
    LinkageSection,
    LocalStorageSection,
    MoveStatement,
    OccursClause,
    OccursSortKey,
    Paragraph,
    ParagraphSummary,
    ParameterType,
    PerformInlineStatement,
    PerformProcedureStatement,
    PerformStatement,
    PerformTimes,
    PerformType,
    PerformUntil,
    PerformVarying,
    PictureClause,
    ProcedureCall,
    ProcedureDivision,
    ProcedureDivisionGivingClause,
    ProcedureDivisionUsingClause,
    Program,
    ProgramUnit,
    RedefinesClause,
    Section,
    SectionCall,
    SignClause,
    SignType,
    SourceLocation,
    Statement,
    StatementType,
    SynchronizedClause,
    SynchronizedType,
    UsageType,
    ValueClause,
    WorkingStorageSection,
)
from src.core.services.cobol_analysis.cobol_parser_antlr_service import (
    IdentificationMetadata,
    ParseNode,
    parse_cobol,
)
from src.core.services.cobol_analysis.cobol_preprocessor_service import (
    CobolPreprocessor,
    PreprocessorConfig,
)


logger = logging.getLogger(__name__)


class ASGBuilderError(ValueError):
    """Raised when ASG cannot be constructed from the provided parse tree."""


# =============================================================================
# Helper Functions
# =============================================================================


def _create_source_location(node: ParseNode) -> SourceLocation | None:
    """Create SourceLocation from ParseNode."""
    if node.line_number is not None:
        return SourceLocation(
            line=node.line_number,
            column=node.column_number or 0,
        )
    return None


def _find_child_node(node: ParseNode, node_type: str) -> ParseNode | None:
    """Find first child node with given type."""
    for child in node.children:
        if isinstance(child, ParseNode) and child.node_type == node_type:
            return child
    return None


def _find_child_value(node: ParseNode, node_type: str) -> str | None:
    """Find first child node with given type and return its value."""
    found = _find_child_node(node, node_type)
    if found and found.value:
        return str(found.value)
    return None


def _walk_nodes(node: ParseNode, target_types: set[str]) -> list[ParseNode]:
    """Walk tree and collect nodes matching target types."""
    result: list[ParseNode] = []

    def _walk(n: ParseNode) -> None:
        if n.node_type in target_types:
            result.append(n)
        for child in n.children:
            if isinstance(child, ParseNode):
                _walk(child)

    _walk(node)
    return result


def _extract_integer_literal_value(node: ParseNode) -> int | None:
    """Extract integer value from INTEGERLITERAL node."""
    if node.value:
        try:
            return int(node.value)
        except (ValueError, TypeError):
            pass

    # Terminal children carry the numeric text in .text, not .value
    for child in node.children:
        if isinstance(child, ParseNode) and child.text:
            try:
                return int(child.text.strip())
            except (ValueError, TypeError):
                pass

    for child in node.children:
        if isinstance(child, ParseNode) and child.node_type == "INTEGERLITERAL" and child.value:
            try:
                return int(child.value)
            except (ValueError, TypeError):
                pass

    return None


def _extract_variable_name(identifier_node: ParseNode | None) -> str | None:
    """Extract variable name from IDENTIFIER node.

    Handles the ANTLR parse tree structure:
    IDENTIFIER > QUALIFIEDDATANAME > QUALIFIEDDATANAMEFORMAT1 > DATANAME > COBOLWORD > IDENTIFIER
    """
    if not identifier_node:
        return None

    if identifier_node.value:
        return str(identifier_node.value)

    # Try direct COBOLWORD child
    cobol_word = _find_child_node(identifier_node, "COBOLWORD")
    if cobol_word:
        inner_id = _find_child_node(cobol_word, "IDENTIFIER")
        if inner_id and inner_id.value:
            return str(inner_id.value)

    # Try QUALIFIEDDATANAME path (IDENTIFIER > QUALIFIEDDATANAME > QUALIFIEDDATANAMEFORMAT1 > DATANAME)
    qualified_name = _find_child_node(identifier_node, "QUALIFIEDDATANAME")
    if qualified_name:
        # Try format 1
        format1 = _find_child_node(qualified_name, "QUALIFIEDDATANAMEFORMAT1")
        if format1:
            dataname = _find_child_node(format1, "DATANAME")
            if dataname and dataname.value:
                return str(dataname.value)
            # Check for COBOLWORD inside DATANAME
            if dataname:
                cw = _find_child_node(dataname, "COBOLWORD")
                if cw:
                    inner_id = _find_child_node(cw, "IDENTIFIER")
                    if inner_id and inner_id.value:
                        return str(inner_id.value)

    # Try DATANAME directly (for data definition contexts)
    dataname = _find_child_node(identifier_node, "DATANAME")
    if dataname and dataname.value:
        return str(dataname.value)
    if dataname:
        cw = _find_child_node(dataname, "COBOLWORD")
        if cw:
            inner_id = _find_child_node(cw, "IDENTIFIER")
            if inner_id and inner_id.value:
                return str(inner_id.value)

    return None


def _extract_literal_value(literal_node: ParseNode | None) -> Any:  # noqa: PLR0911
    """Extract value from LITERAL node."""
    if not literal_node:
        return None

    numeric_literal = _find_child_node(literal_node, "NUMERICLITERAL")
    if numeric_literal:
        if numeric_literal.value:
            return _parse_numeric_literal(numeric_literal)
        int_literal = _find_child_node(numeric_literal, "INTEGERLITERAL")
        if int_literal:
            value = _extract_integer_literal_value(int_literal)
            if value is not None:
                return value

    nonnumeric = _find_child_node(literal_node, "NONNUMERICLITERAL")
    if nonnumeric:
        if nonnumeric.value:
            return str(nonnumeric.value).strip("'\"")
        # Value may be in terminal child's .text
        for child in nonnumeric.children:
            if isinstance(child, ParseNode) and child.text:
                return str(child.text).strip("'\"")

    # Check for figurative constant
    figurative = _find_child_node(literal_node, "FIGURATIVECONSTANT")
    if figurative:
        return _extract_figurative_constant(figurative)

    if literal_node.value:
        return literal_node.value

    # Fallback: TERMINALNODEIMPL children (e.g., LITERAL > TERMINALNODEIMPL text='N')
    for child in literal_node.children:
        if isinstance(child, ParseNode) and child.node_type == "TERMINALNODEIMPL":
            text = (child.text or "").strip()
            if text:
                return text.strip("'\"")

    return None


def _parse_numeric_literal(numeric_node: ParseNode) -> int | float | None:
    """Parse numeric literal node to Python number."""
    value_str = str(numeric_node.value) if numeric_node.value else ""
    if not value_str:
        return None

    try:
        if "." in value_str or "E" in value_str.upper():
            return float(value_str)
        return int(value_str)
    except ValueError:
        return None


def _extract_figurative_constant(figurative: ParseNode) -> Any:
    """Extract value from FIGURATIVECONSTANT node."""
    figurative_map = {
        "ZERO": 0,
        "ZEROS": 0,
        "ZEROES": 0,
        "SPACE": " ",
        "SPACES": " ",
        "HIGH-VALUE": "HIGH-VALUE",
        "HIGH-VALUES": "HIGH-VALUE",
        "LOW-VALUE": "LOW-VALUE",
        "LOW-VALUES": "LOW-VALUE",
        "QUOTE": '"',
        "QUOTES": '"',
        "NULL": None,
        "NULLS": None,
    }

    for child in figurative.children:
        if not isinstance(child, ParseNode):
            continue
        # Terminal nodes carry content in .text, parse nodes in .value
        token = child.value or child.text
        if token:
            fig_value = str(token).strip().upper()
            if fig_value in figurative_map:
                return figurative_map[fig_value]
            return fig_value

    return None


def _extract_condition_text(condition_node: ParseNode) -> str:
    """Extract human-readable condition text from CONDITION node."""
    parts: list[str] = []

    def collect_terminal_values(node: ParseNode) -> None:
        has_parse_children = any(isinstance(c, ParseNode) for c in node.children)

        # Leaf node: collect value or text (terminals carry content in .text)
        if not has_parse_children:
            token = node.value or node.text
            if token:
                parts.append(str(token).strip())
        else:
            for child in node.children:
                if isinstance(child, ParseNode):
                    collect_terminal_values(child)

    collect_terminal_values(condition_node)
    return " ".join(parts) if parts else ""


# =============================================================================
# Main ASG Builder
# =============================================================================


def build_asg(
    parse_tree: ParseNode,
    source_file: str = "unknown",
    id_metadata: IdentificationMetadata | None = None,
) -> Program:
    """Build Abstract Semantic Graph from ANTLR parse tree.

    Args:
        parse_tree: Root ParseNode from ANTLR parser
        source_file: Source file path for metadata
        id_metadata: Optional identification metadata (AUTHOR, DATE-WRITTEN, etc.)

    Returns:
        Program object containing the full ASG

    Raises:
        ASGBuilderError: If parse tree is invalid
    """
    if not isinstance(parse_tree, ParseNode):
        raise ASGBuilderError("Parse tree must be a ParseNode instance.")

    if parse_tree.node_type != "PROGRAM":
        raise ASGBuilderError(f"Expected root node type 'PROGRAM', got '{parse_tree.node_type}'.")

    # Build program units from parse tree
    program_units: list[ProgramUnit] = []
    program_unit = _build_program_unit(parse_tree, id_metadata)
    program_units.append(program_unit)

    # Create compilation unit
    compilation_unit = CompilationUnit(
        program_units=program_units,
    )

    # Extract external calls for cross-program analysis
    external_calls = _extract_external_calls(program_unit)

    # Create program
    return Program(
        source_file=source_file,
        source_format="FIXED",
        parser_version="2.0-python",
        compilation_units=[compilation_unit],
        external_calls=external_calls,
        analysis_timestamp=datetime.now().isoformat(),
    )


def _build_program_unit(
    node: ParseNode,
    id_metadata: IdentificationMetadata | None = None,
) -> ProgramUnit:
    """Build ProgramUnit from parse tree."""
    # Build each division
    id_division = None
    env_division = None
    data_division = None
    proc_division = None

    for child in node.children:
        if isinstance(child, ParseNode):
            if child.node_type == "IDENTIFICATION_DIVISION":
                id_division = _build_identification_division(child, id_metadata)
            elif child.node_type == "ENVIRONMENT_DIVISION":
                env_division = _build_environment_division(child)
            elif child.node_type == "DATA_DIVISION":
                data_division = _build_data_division(child)
            elif child.node_type == "PROCEDURE_DIVISION":
                proc_division = _build_procedure_division(child)

    if id_division is None:
        id_division = IdentificationDivision(program_id="UNKNOWN")

    # Resolve cross-references (data item usage tracking)
    _resolve_cross_references(data_division, proc_division)

    return ProgramUnit(
        identification_division=id_division,
        environment_division=env_division,
        data_division=data_division,
        procedure_division=proc_division,
    )


# =============================================================================
# Identification Division Builder
# =============================================================================


def _build_identification_division(
    node: ParseNode,
    id_metadata: IdentificationMetadata | None = None,
) -> IdentificationDivision:
    """Build IdentificationDivision from parse tree."""
    # Extract PROGRAM-ID - search recursively for PROGRAM_NAME node
    program_id = "UNKNOWN"

    # Walk the tree to find PROGRAM_NAME (which contains the actual name)
    program_name_nodes = _walk_nodes(node, {"PROGRAM_NAME"})
    if program_name_nodes:
        name_node = program_name_nodes[0]
        if name_node.value:
            program_id = str(name_node.value)

    # Build division with metadata
    division = IdentificationDivision(
        program_id=program_id,
        location=_create_source_location(node),
    )

    # Add metadata from preprocessing
    if id_metadata:
        division.author = id_metadata.author
        division.installation = id_metadata.installation
        division.date_written = id_metadata.date_written
        division.date_compiled = id_metadata.date_compiled
        division.security = id_metadata.security
        division.remarks = id_metadata.remarks

    return division


# =============================================================================
# Environment Division Builder
# =============================================================================


def _build_environment_division(node: ParseNode) -> EnvironmentDivision:
    """Build EnvironmentDivision from parse tree."""
    input_output_section = None

    # Build INPUT-OUTPUT SECTION
    io_sections = _walk_nodes(node, {"INPUTOUTPUTSECTION"})
    io_section = io_sections[0] if io_sections else None
    if io_section:
        file_entries: list[FileControlEntry] = []

        for file_control in _walk_nodes(io_section, {"FILECONTROLENTRY"}):
            entry = _build_file_control_entry(file_control)
            if entry:
                file_entries.append(entry)

        input_output_section = InputOutputSection(
            file_control_entries=file_entries,
            location=_create_source_location(io_section),
        )

    return EnvironmentDivision(
        input_output_section=input_output_section,
        location=_create_source_location(node),
    )


def _build_file_control_entry(node: ParseNode) -> FileControlEntry | None:
    """Build FileControlEntry from FILECONTROLENTRY node."""
    # FILENAME is inside SELECTCLAUSE, so walk the subtree
    filename_nodes = _walk_nodes(node, {"FILENAME"})
    file_name = filename_nodes[0].value if filename_nodes and filename_nodes[0].value else None
    if not file_name:
        return None

    # Extract ASSIGN TO value from ASSIGNCLAUSE
    assign_nodes = _walk_nodes(node, {"ASSIGNCLAUSE"})
    assign_to = None
    if assign_nodes:
        literal_nodes = _walk_nodes(assign_nodes[0], {"LITERAL"})
        if literal_nodes:
            # Value may be in terminal child's text attribute
            for child in literal_nodes[0].children:
                text = getattr(child, "text", None) or child.value
                if text:
                    assign_to = str(text).strip("'\"")
                    break

    # Extract organization from ORGANIZATIONCLAUSE
    org_nodes = _walk_nodes(node, {"ORGANIZATIONCLAUSE"})
    org_str = None
    if org_nodes:
        for child in org_nodes[0].children:
            text = getattr(child, "text", None) or child.value
            if text:
                val = str(text).upper()
                if val in ("SEQUENTIAL", "INDEXED", "RELATIVE", "LINE"):
                    org_str = val
                    break

    organization = None
    if org_str:
        org_map = {
            "SEQUENTIAL": FileOrganization.SEQUENTIAL,
            "INDEXED": FileOrganization.INDEXED,
            "RELATIVE": FileOrganization.RELATIVE,
            "LINE": FileOrganization.LINE_SEQUENTIAL,
        }
        organization = org_map.get(org_str.upper())

    return FileControlEntry(
        name=file_name,
        file_name=file_name,
        assign_to=assign_to,
        organization=organization,
        location=_create_source_location(node),
    )


# =============================================================================
# Data Division Builder
# =============================================================================


def _build_data_division(node: ParseNode) -> DataDivision:
    """Build DataDivision from parse tree."""
    working_storage = None
    linkage_section = None
    local_storage = None
    file_section = None

    # Build sections - walk tree to find sections (they may be nested in DATADIVISIONSECTION)
    ws_sections = _walk_nodes(node, {"WORKING_STORAGE_SECTION"})
    if ws_sections:
        entries = _build_data_entries(ws_sections[0])
        working_storage = WorkingStorageSection(
            entries=entries,
            location=_create_source_location(ws_sections[0]),
        )

    ls_sections = _walk_nodes(node, {"LINKAGE_SECTION"})
    if ls_sections:
        entries = _build_data_entries(ls_sections[0])
        linkage_section = LinkageSection(
            entries=entries,
            location=_create_source_location(ls_sections[0]),
        )

    loc_sections = _walk_nodes(node, {"LOCAL_STORAGE_SECTION"})
    if loc_sections:
        entries = _build_data_entries(loc_sections[0])
        local_storage = LocalStorageSection(
            entries=entries,
            location=_create_source_location(loc_sections[0]),
        )

    fs_sections = _walk_nodes(node, {"FILE_SECTION"})
    if fs_sections:
        file_section = _build_file_section(fs_sections[0])

    return DataDivision(
        working_storage=working_storage,
        linkage_section=linkage_section,
        local_storage=local_storage,
        file_section=file_section,
        location=_create_source_location(node),
    )


def _build_data_entries(section_node: ParseNode) -> list[DataDescriptionEntry]:
    """Build list of data entries from section node."""
    entries: list[DataDescriptionEntry] = []

    for entry_node in _walk_nodes(section_node, {"DATADESCRIPTIONENTRY"}):
        entry = _build_data_description_entry(entry_node)
        if entry:
            entries.append(entry)

    # Build hierarchical structure
    return _build_entry_hierarchy(entries)


def _build_data_description_entry(node: ParseNode) -> DataDescriptionEntry | None:
    """Build DataDescriptionEntry with all clause types."""
    # Find format node
    format_node = None
    for child in node.children:
        if isinstance(child, ParseNode) and child.node_type.startswith(
            "DATADESCRIPTIONENTRYFORMAT"
        ):
            format_node = child
            break

    if not format_node:
        return None

    # Extract basic info
    level = _extract_level_number(format_node)
    name = _extract_data_name(format_node) or "FILLER"

    # Determine entry type
    entry_type = _determine_entry_type(level, format_node)

    # Create entry
    entry = DataDescriptionEntry(
        name=name,
        level=level or 1,
        entry_type=entry_type,
        is_filler=name == "FILLER",
        location=_create_source_location(node),
    )

    # Extract all clauses
    _extract_picture_clause(format_node, entry)
    _extract_usage_clause(format_node, entry)
    _extract_value_clause(format_node, entry)
    _extract_occurs_clause(format_node, entry)
    _extract_redefines_clause(format_node, entry)
    _extract_sync_clause(format_node, entry)
    _extract_sign_clause(format_node, entry)
    _extract_justified_clause(format_node, entry)
    _extract_blank_when_zero_clause(format_node, entry)
    _extract_external_clause(format_node, entry)
    _extract_global_clause(format_node, entry)

    # Handle Level 88 conditions
    if level == 88:
        _extract_condition_values(format_node, entry)

    # Handle Level 66 renames
    if level == 66:
        _extract_renames_info(format_node, entry)

    return entry


def _determine_entry_type(level: int | None, format_node: ParseNode) -> DataDescriptionEntryType:
    """Determine the entry type based on level and structure."""
    if level == 88:
        return DataDescriptionEntryType.CONDITION
    if level == 66:
        return DataDescriptionEntryType.RENAME
    if level == 77:
        return DataDescriptionEntryType.SCALAR

    # Check if GROUP (has subordinate items) or ELEMENTARY (has PICTURE)
    has_picture = _find_child_node(format_node, "DATAPICTURECLAUSE") is not None
    if has_picture:
        return DataDescriptionEntryType.ELEMENTARY

    return DataDescriptionEntryType.GROUP


def _extract_level_number(format_node: ParseNode) -> int | None:
    """Extract level number from data description entry.

    Level numbers appear as:
    - LEVEL_NUMBER_88 node (for level 88)
    - LEVEL_NUMBER_66 node (for level 66)
    - INTEGERLITERAL node (for regular levels in some grammars)
    - TERMINALNODEIMPL with text like '01', '05', '88' (ANTLR terminals)
    """
    # Check for Level 88 node or format3 (level 88 condition)
    if _find_child_node(format_node, "LEVEL_NUMBER_88"):
        return 88
    if format_node.node_type == "DATADESCRIPTIONENTRYFORMAT3":
        return 88

    # Check for Level 66 node or format2 (level 66 renames)
    if _find_child_node(format_node, "LEVEL_NUMBER_66"):
        return 66
    if format_node.node_type == "DATADESCRIPTIONENTRYFORMAT2":
        return 66

    # Regular level number from INTEGERLITERAL
    int_literal = _find_child_node(format_node, "INTEGERLITERAL")
    if int_literal:
        return _extract_integer_literal_value(int_literal)

    # Level number as first TERMINALNODEIMPL child (e.g., text='01', '05', '77')
    for child in format_node.children:
        if isinstance(child, ParseNode) and child.node_type == "TERMINALNODEIMPL":
            text = (child.text or "").strip()
            if text.isdigit():
                return int(text)

    return None


def _extract_data_name(format_node: ParseNode) -> str | None:
    """Extract data name from format node.

    Handles both pre-populated .value and ANTLR terminal structure:
    DATANAME value=X  or  DATANAME > COBOLWORD > TERMINALNODEIMPL text=X
    CONDITIONNAME value=X  or  CONDITIONNAME > COBOLWORD > TERMINALNODEIMPL text=X
    """
    for node_type in ("DATANAME", "CONDITIONNAME"):
        node = _find_child_node(format_node, node_type)
        if not node:
            continue
        # Pre-populated value
        if node.value:
            return str(node.value)
        # Walk into COBOLWORD > TERMINALNODEIMPL to get .text
        cobol_word = _find_child_node(node, "COBOLWORD")
        if cobol_word:
            if cobol_word.value:
                return str(cobol_word.value)
            for child in cobol_word.children:
                if isinstance(child, ParseNode) and child.node_type == "TERMINALNODEIMPL":
                    text = (child.text or "").strip()
                    if text:
                        return text

    return None


def _extract_picture_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract PICTURE clause and analyze it."""
    pic_clause = _find_child_node(format_node, "DATAPICTURECLAUSE")
    if not pic_clause:
        return

    pic_string = _find_child_node(pic_clause, "PICTURESTRING")
    if not pic_string:
        return

    # Build picture string
    parts: list[str] = []
    for child in pic_string.children:
        if isinstance(child, ParseNode) and child.node_type == "PICTURECHARS":
            for subchild in child.children:
                if isinstance(subchild, ParseNode):
                    if subchild.node_type == "INTEGERLITERAL":
                        value = _extract_integer_literal_value(subchild)
                        if value is not None:
                            parts.append(str(value))
                    elif subchild.value:
                        parts.append(str(subchild.value))
                    elif subchild.text:
                        # Terminal tokens carry the PIC character in .text
                        parts.append(subchild.text)

    pic_str = "".join(parts)
    if pic_str:
        entry.picture = _analyze_picture(pic_str)


def _analyze_picture(pic_str: str) -> PictureClause:
    """Analyze PICTURE string and determine properties."""
    pic_upper = pic_str.upper()

    # Determine category based on which significant PIC characters are present
    # Include both letters and '9' as significant characters (exclude digits in parens, parens themselves)
    pic_significant = {c for c in pic_upper if c.isalpha() or c == "9"}
    has_9 = "9" in pic_significant
    has_x = "X" in pic_significant
    has_a_only = pic_significant <= {"A"} and bool(pic_significant)
    numeric_chars = {"S", "P", "V", "B", "Z", "C", "R", "D", "9"}
    is_numeric = bool(pic_significant) and pic_significant <= numeric_chars and has_9
    is_alphabetic = has_a_only
    is_alphanumeric = has_x or (not is_numeric and not is_alphabetic)

    # Check for editing symbols
    is_edited = any(c in pic_upper for c in "Z*$,.+-CRDB")
    is_numeric_edited = is_numeric and is_edited
    is_alpha_edited = is_alphanumeric and is_edited

    # Determine category string
    if is_numeric and not is_edited:
        category = "NUMERIC"
    elif is_numeric_edited:
        category = "NUMERIC_EDITED"
    elif is_alphabetic:
        category = "ALPHABETIC"
    elif is_alpha_edited:
        category = "ALPHANUMERIC_EDITED"
    else:
        category = "ALPHANUMERIC"

    # Calculate size
    size = _calculate_picture_size(pic_str)

    # Count decimal positions
    decimal_positions = 0
    if "V" in pic_upper:
        after_v = pic_upper.split("V")[-1]
        decimal_positions = sum(1 for c in after_v if c == "9")

    return PictureClause(
        picture_string=pic_str,
        category=category,
        size=size,
        decimal_positions=decimal_positions,
        is_signed="S" in pic_upper or "+" in pic_upper or "-" in pic_upper,
        is_numeric=is_numeric and not is_edited,
        is_alphabetic=is_alphabetic,
        is_alphanumeric=is_alphanumeric and not is_edited,
        is_numeric_edited=is_numeric_edited,
        is_alphanumeric_edited=is_alpha_edited,
    )


def _calculate_picture_size(pic_str: str) -> int:
    """Calculate size from PICTURE string."""
    size = 0
    i = 0
    pic_upper = pic_str.upper()

    while i < len(pic_upper):
        char = pic_upper[i]

        if char == "(":
            # Find the number in parentheses
            j = i + 1
            num_str = ""
            while j < len(pic_upper) and pic_upper[j] != ")":
                num_str += pic_upper[j]
                j += 1
            try:
                repeat = int(num_str)
                size += repeat - 1  # -1 because the char before was already counted
            except ValueError:
                pass
            i = j + 1
        elif char in "9AXVSPZ*$":
            size += 1
            i += 1
        else:
            i += 1

    return max(1, size)


def _extract_usage_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract USAGE clause."""
    usage_clause = _find_child_node(format_node, "DATAUSAGECLAUSE")
    if not usage_clause:
        return

    usage_map = {
        "COMP": UsageType.COMP,
        "COMP_1": UsageType.COMP_1,
        "COMP_2": UsageType.COMP_2,
        "COMP_3": UsageType.COMP_3,
        "COMP_4": UsageType.COMP_4,
        "COMP_5": UsageType.COMP_5,
        "COMPUTATIONAL": UsageType.COMPUTATIONAL,
        "COMPUTATIONAL_1": UsageType.COMPUTATIONAL_1,
        "COMPUTATIONAL_2": UsageType.COMPUTATIONAL_2,
        "COMPUTATIONAL_3": UsageType.COMPUTATIONAL_3,
        "COMPUTATIONAL_4": UsageType.COMPUTATIONAL_4,
        "COMPUTATIONAL_5": UsageType.COMPUTATIONAL_5,
        "DISPLAY": UsageType.DISPLAY,
        "DISPLAY_1": UsageType.DISPLAY_1,
        "BINARY": UsageType.BINARY,
        "PACKED_DECIMAL": UsageType.PACKED_DECIMAL,
        "INDEX": UsageType.INDEX,
        "POINTER": UsageType.POINTER,
        "POINTER_32": UsageType.POINTER_32,
        "PROCEDURE_POINTER": UsageType.PROCEDURE_POINTER,
        "FUNCTION_POINTER": UsageType.FUNCTION_POINTER,
        "NATIONAL": UsageType.NATIONAL,
    }

    for child in usage_clause.children:
        if isinstance(child, ParseNode):
            node_type = child.node_type.replace("-", "_").upper()
            if node_type in usage_map:
                entry.usage = usage_map[node_type]
                return
            # Check .value then .text — terminal tokens carry text in .text
            token_value = child.value or child.text
            if token_value:
                value = str(token_value).replace("-", "_").upper()
                if value in usage_map:
                    entry.usage = usage_map[value]
                    return


def _extract_value_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract VALUE clause.

    Parse tree structure:
    DATAVALUECLAUSE > DATAVALUEINTERVAL > DATAVALUEINTERVALFROM > LITERAL
    or direct: DATAVALUECLAUSE > LITERAL
    """
    value_clause = _find_child_node(format_node, "DATAVALUECLAUSE")
    if not value_clause:
        return

    # Walk the tree to find LITERAL or FIGURATIVECONSTANT at any depth
    literals = _walk_nodes(value_clause, {"LITERAL"})
    if literals:
        literal = literals[0]
        # Check if the LITERAL contains a FIGURATIVECONSTANT
        figurative = _find_child_node(literal, "FIGURATIVECONSTANT")
        if figurative:
            value = _extract_figurative_constant(figurative)
            entry.value = ValueClause(value=value, value_type="FIGURATIVE")
        else:
            value = _extract_literal_value(literal)
            entry.value = ValueClause(value=value, value_type="LITERAL")
        return

    # Direct figurative constant (not nested in LITERAL)
    figuratives = _walk_nodes(value_clause, {"FIGURATIVECONSTANT"})
    if figuratives:
        value = _extract_figurative_constant(figuratives[0])
        entry.value = ValueClause(value=value, value_type="FIGURATIVE")


def _extract_occurs_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract OCCURS clause with all details."""
    occurs_clause = _find_child_node(format_node, "DATAOCCURSCLAUSE")
    if not occurs_clause:
        return

    # Extract count values
    integers: list[int] = []
    for child in occurs_clause.children:
        if isinstance(child, ParseNode) and child.node_type == "INTEGERLITERAL":
            val = _extract_integer_literal_value(child)
            if val is not None:
                integers.append(val)

    from_value = None
    to_value = None
    min_occurs = 1
    max_occurs = None

    if len(integers) == 1:
        max_occurs = integers[0]
        min_occurs = integers[0]
    elif len(integers) >= 2:
        from_value = integers[0]
        to_value = integers[1]
        min_occurs = from_value
        max_occurs = to_value

    # Extract DEPENDING ON
    depending_on_name = None
    depending = _find_child_node(occurs_clause, "DATAOCCURSDEPENDING")
    if depending:
        identifier = _find_child_node(depending, "IDENTIFIER")
        depending_on_name = _extract_variable_name(identifier)

    # Extract INDEXED BY
    indexed_by: list[str] = []
    indexed = _find_child_node(occurs_clause, "DATAOCCURSINDEXED")
    if indexed:
        index_name = _extract_variable_name(_find_child_node(indexed, "IDENTIFIER"))
        if index_name:
            indexed_by.append(index_name)

    # Extract KEY IS
    sort_keys: list[OccursSortKey] = []
    for sort_node in _walk_nodes(occurs_clause, {"DATAOCCURSSORT"}):
        key_name = _extract_variable_name(_find_child_node(sort_node, "IDENTIFIER"))
        is_ascending = _find_child_node(sort_node, "ASCENDING") is not None
        if key_name:
            sort_keys.append(
                OccursSortKey(
                    key_name=key_name,
                    is_ascending=is_ascending,
                )
            )

    entry.occurs = OccursClause(
        from_value=from_value,
        to_value=to_value,
        depending_on_name=depending_on_name,
        indexed_by=indexed_by,
        sort_keys=sort_keys,
        min_occurs=min_occurs,
        max_occurs=max_occurs,
    )


def _extract_redefines_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract REDEFINES clause."""
    redefines_clause = _find_child_node(format_node, "DATAREDEFINESCLAUSE")
    if not redefines_clause:
        return

    dataname = _find_child_node(redefines_clause, "DATANAME")
    if dataname:
        cobol_word = _find_child_node(dataname, "COBOLWORD")
        if cobol_word:
            identifier = _find_child_node(cobol_word, "IDENTIFIER")
            if identifier and identifier.value:
                entry.redefines = RedefinesClause(redefines_name=str(identifier.value))


def _extract_sync_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract SYNCHRONIZED clause."""
    sync_clause = _find_child_node(format_node, "DATASYNCHRONIZEDCLAUSE")
    if not sync_clause:
        return

    sync_type = None
    if _find_child_node(sync_clause, "LEFT"):
        sync_type = SynchronizedType.LEFT
    elif _find_child_node(sync_clause, "RIGHT"):
        sync_type = SynchronizedType.RIGHT

    entry.synchronized = SynchronizedClause(synchronized_type=sync_type)


def _extract_sign_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract SIGN clause."""
    sign_clause = _find_child_node(format_node, "DATASIGNCLAUSE")
    if not sign_clause:
        return

    is_leading = _find_child_node(sign_clause, "LEADING") is not None
    is_trailing = _find_child_node(sign_clause, "TRAILING") is not None
    is_separate = _find_child_node(sign_clause, "SEPARATE") is not None

    if is_leading:
        sign_type = SignType.LEADING_SEPARATE if is_separate else SignType.LEADING
    elif is_trailing:
        sign_type = SignType.TRAILING_SEPARATE if is_separate else SignType.TRAILING
    else:
        sign_type = SignType.TRAILING

    entry.sign_clause = SignClause(sign_type=sign_type, is_separate=is_separate)
    entry.sign_type = sign_type


def _extract_justified_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract JUSTIFIED clause."""
    justified_clause = _find_child_node(format_node, "DATAJUSTIFIEDCLAUSE")
    if justified_clause:
        entry.justified = JustifiedClause(is_right=True)
        entry.is_justified_right = True


def _extract_blank_when_zero_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract BLANK WHEN ZERO clause."""
    blank_clause = _find_child_node(format_node, "DATABLANKWHENZEROCLAUSE")
    if blank_clause:
        entry.blank_when_zero = BlankWhenZeroClause(is_blank_when_zero=True)
        entry.is_blank_when_zero = True


def _extract_external_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract EXTERNAL clause."""
    external_clause = _find_child_node(format_node, "DATAEXTERNALCLAUSE")
    if external_clause:
        entry.external = ExternalClause(is_external=True)
        entry.is_external = True


def _extract_global_clause(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract GLOBAL clause."""
    global_clause = _find_child_node(format_node, "DATAGLOBALCLAUSE")
    if global_clause:
        entry.global_clause = GlobalClause(is_global=True)
        entry.is_global = True


def _extract_condition_values(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract Level 88 condition values.

    Parse tree structure:
    DATAVALUECLAUSE > DATAVALUEINTERVAL > DATAVALUEINTERVALFROM > LITERAL
    """
    values: list[Any] = []

    for value_clause in _walk_nodes(format_node, {"DATAVALUECLAUSE"}):
        # Walk to find all LITERAL nodes at any depth
        for literal in _walk_nodes(value_clause, {"LITERAL"}):
            # Check for figurative constant inside literal
            figurative = _find_child_node(literal, "FIGURATIVECONSTANT")
            if figurative:
                value = _extract_figurative_constant(figurative)
            else:
                value = _extract_literal_value(literal)
            if value is not None:
                values.append(value)

    entry.condition_values = values if values else None


def _extract_renames_info(format_node: ParseNode, entry: DataDescriptionEntry) -> None:
    """Extract Level 66 renames info."""
    renames_clause = _find_child_node(format_node, "DATARENAMECLAUSE")
    if not renames_clause:
        return

    # Extract FROM item
    identifiers = _walk_nodes(renames_clause, {"IDENTIFIER"})
    if identifiers:
        entry.renames_from = _extract_variable_name(identifiers[0])
        if len(identifiers) > 1:
            entry.renames_through = _extract_variable_name(identifiers[1])


def _build_entry_hierarchy(entries: list[DataDescriptionEntry]) -> list[DataDescriptionEntry]:
    """Build hierarchical structure from flat list based on level numbers."""
    if not entries:
        return []

    root_entries: list[DataDescriptionEntry] = []
    stack: list[DataDescriptionEntry] = []

    for entry in entries:
        level = entry.level

        # Pop entries from stack until we find parent
        while stack and stack[-1].level >= level:
            stack.pop()

        if stack:
            # Add as child of current parent
            stack[-1].children.append(entry)
            entry.parent_name = stack[-1].name
        else:
            # Root level entry
            root_entries.append(entry)

        # Push to stack if this could be a parent (not level 88 or 66)
        if level not in (66, 88):
            stack.append(entry)

    return root_entries


def _build_file_section(node: ParseNode) -> FileSection:
    """Build FileSection from FILE_SECTION node."""
    file_descriptions: list[FileDescriptionEntry] = []

    for fd_node in _walk_nodes(node, {"FILEDESCRIPTIONENTRY"}):
        fd = _build_file_description_entry(fd_node)
        if fd:
            file_descriptions.append(fd)

    return FileSection(
        file_descriptions=file_descriptions,
        location=_create_source_location(node),
    )


def _build_file_description_entry(node: ParseNode) -> FileDescriptionEntry | None:
    """Build FileDescriptionEntry from FD node."""
    file_name = _find_child_value(node, "FILENAME")
    if not file_name:
        return None

    record_entries: list[DataDescriptionEntry] = []
    for entry_node in _walk_nodes(node, {"DATADESCRIPTIONENTRY"}):
        entry = _build_data_description_entry(entry_node)
        if entry:
            record_entries.append(entry)

    return FileDescriptionEntry(
        name=file_name,
        file_type="FD",
        record_entries=_build_entry_hierarchy(record_entries),
        location=_create_source_location(node),
    )


# =============================================================================
# Procedure Division Builder
# =============================================================================


def _build_procedure_division(node: ParseNode) -> ProcedureDivision:
    """Build ProcedureDivision from parse tree."""
    sections: list[Section] = []
    paragraphs: list[Paragraph] = []
    all_paragraphs: list[ParagraphSummary] = []
    call_statements: list[CallStatement] = []

    # Extract USING clause
    # ANTLR structure: PROCEDUREDIVISIONUSINGCLAUSE -> PROCEDUREDIVISIONUSINGPARAMETER
    #   -> PROCEDUREDIVISIONBYREFERENCEPHRASE -> PROCEDUREDIVISIONBYREFERENCE
    #   -> IDENTIFIER -> QUALIFIEDDATANAME -> QUALIFIEDDATANAMEFORMAT1 -> DATANAME
    using_clause = None
    using_parameters: list[str] = []
    using_node = _find_child_node(node, "PROCEDUREDIVISIONUSINGCLAUSE")
    if using_node:
        # Walk for DATANAME nodes to get parameter names
        for dataname in _walk_nodes(using_node, {"DATANAME"}):
            if dataname.value:
                using_parameters.append(str(dataname.value))
        using_clause = ProcedureDivisionUsingClause(parameter_names=using_parameters)

    # Extract GIVING clause
    # ANTLR structure: PROCEDUREDIVISIONGIVINGCLAUSE -> DATANAME
    giving_clause = None
    returning_parameter = None
    giving_node = _find_child_node(node, "PROCEDUREDIVISIONGIVINGCLAUSE")
    if giving_node:
        dataname_node = _find_child_node(giving_node, "DATANAME")
        if dataname_node is not None and dataname_node.value:
            returning_parameter = str(dataname_node.value)
        giving_clause = ProcedureDivisionGivingClause(giving_name=returning_parameter)

    # Find PROCEDURE_BODY which contains PARAGRAPHS and PROCEDURESECTION
    proc_body = _find_child_node(node, "PROCEDURE_BODY")
    if proc_body:
        # Process children in order to get top-level paragraphs and sections
        for child in proc_body.children:
            if not isinstance(child, ParseNode):
                continue

            if child.node_type == "PARAGRAPHS":
                # Top-level paragraphs (not in any section)
                for para_node in _walk_nodes(child, {"PARAGRAPH"}):
                    paragraph = _build_paragraph(para_node)
                    if paragraph:
                        paragraphs.append(paragraph)
                        all_paragraphs.append(
                            ParagraphSummary(
                                name=paragraph.name or "UNKNOWN",
                                section_name=paragraph.section_name,
                            )
                        )
                        _collect_call_statements(paragraph, call_statements)

            elif child.node_type == "PROCEDURESECTION":
                # Build section with its paragraphs
                section = _build_section(child)
                if section:
                    sections.append(section)
                    all_paragraphs.extend(
                        ParagraphSummary(
                            name=p.name or "UNKNOWN",
                            section_name=p.section_name or section.name,
                        )
                        for p in section.paragraphs
                    )
                    for para in section.paragraphs:
                        _collect_call_statements(para, call_statements)

    return ProcedureDivision(
        sections=sections,
        paragraphs=paragraphs,
        all_paragraphs=all_paragraphs,
        using_clause=using_clause,
        using_parameters=using_parameters,
        giving_clause=giving_clause,
        returning_parameter=returning_parameter,
        call_statements=call_statements,
        location=_create_source_location(node),
    )


def _collect_call_statements(paragraph: Paragraph, call_statements: list[CallStatement]) -> None:
    """Collect CALL statements from a paragraph."""
    for stmt in paragraph.statements:
        if stmt.statement_type == StatementType.CALL and stmt.call_details:
            call_statements.append(stmt.call_details)


def _build_section(node: ParseNode) -> Section | None:
    """Build Section from PROCEDURESECTION node.

    ANTLR structure:
        PROCEDURESECTION
            PROCEDURESECTIONHEADER
                SECTIONNAME -> COBOLWORD -> IDENTIFIER
                SECTION
            PARAGRAPHS
                PARAGRAPH...
    """
    section_name = None

    # Get section name from header
    header = _find_child_node(node, "PROCEDURESECTIONHEADER")
    if header:
        section_name_node = _find_child_node(header, "SECTIONNAME")
        if section_name_node:
            # Get the identifier value
            for cobolword in _walk_nodes(section_name_node, {"COBOLWORD", "IDENTIFIER"}):
                if cobolword.value:
                    section_name = str(cobolword.value)
                    break

    if not section_name:
        return None

    # Build paragraphs within this section
    section_paragraphs: list[Paragraph] = []
    paragraphs_node = _find_child_node(node, "PARAGRAPHS")
    if paragraphs_node:
        for para_node in _walk_nodes(paragraphs_node, {"PARAGRAPH"}):
            paragraph = _build_paragraph(para_node)
            if paragraph:
                section_paragraphs.append(paragraph)

    return Section(
        name=section_name,
        paragraphs=section_paragraphs,
        location=_create_source_location(node),
    )


def _build_paragraph(node: ParseNode) -> Paragraph | None:
    """Build Paragraph from PARAGRAPH node."""
    paragraph_name = _find_child_value(node, "PARAGRAPH_NAME")
    if not paragraph_name:
        # Try alternative structure
        for child in node.children:
            if (
                isinstance(child, ParseNode)
                and child.value
                and child.node_type in ("PARAGRAPH_NAME", "PARAGRAPHNAME")
            ):
                paragraph_name = str(child.value)
                break

    if not paragraph_name:
        paragraph_name = "PARAGRAPH"

    statements: list[Statement] = []

    # Collect only top-level STATEMENT nodes from each sentence.
    # Using direct children (not _walk_nodes) avoids pulling nested statements
    # from inside IF/ELSE branches into the paragraph's flat list — those
    # belong to the IF model's then_statements/else_statements and are
    # processed by the cross-reference resolver through recursion there.
    for sentence in _walk_nodes(node, {"SENTENCE"}):
        for stmt_wrapper in sentence.children:
            if not isinstance(stmt_wrapper, ParseNode) or stmt_wrapper.node_type != "STATEMENT":
                continue
            for child in stmt_wrapper.children:
                if isinstance(child, ParseNode):
                    stmt = _build_statement(child)
                    if stmt:
                        statements.append(stmt)

    statement_types = [s.statement_type for s in statements]

    return Paragraph(
        name=paragraph_name,
        paragraph_name=paragraph_name,
        statements=statements,
        statement_count=len(statements),
        statement_types=statement_types,
        location=_create_source_location(node),
    )


def _build_statement(node: ParseNode) -> Statement | None:
    """Build Statement from statement node."""
    # Map node types to statement types and builders
    statement_builders = {
        "CALLSTATEMENT": _build_call_statement,
        "CALL_STATEMENT": _build_call_statement,
        "PERFORMSTATEMENT": _build_perform_statement,
        "PERFORM_STATEMENT": _build_perform_statement,
        "IFSTATEMENT": _build_if_statement,
        "IF_STATEMENT": _build_if_statement,
        "EVALUATESTATEMENT": _build_evaluate_statement,
        "EVALUATE_STATEMENT": _build_evaluate_statement,
        "MOVESTATEMENT": _build_move_statement,
        "MOVE_STATEMENT": _build_move_statement,
        "COMPUTESTATEMENT": _build_compute_statement,
        "COMPUTE_STATEMENT": _build_compute_statement,
        "ADDSTATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.ADD),
        "ADD_STATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.ADD),
        "SUBTRACTSTATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.SUBTRACT),
        "SUBTRACT_STATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.SUBTRACT),
        "MULTIPLYSTATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.MULTIPLY),
        "MULTIPLY_STATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.MULTIPLY),
        "DIVIDESTATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.DIVIDE),
        "DIVIDE_STATEMENT": lambda n: _build_arithmetic_statement(n, StatementType.DIVIDE),
        "READSTATEMENT": lambda n: _build_io_statement(n, StatementType.READ),
        "READ_STATEMENT": lambda n: _build_io_statement(n, StatementType.READ),
        "WRITESTATEMENT": lambda n: _build_io_statement(n, StatementType.WRITE),
        "WRITE_STATEMENT": lambda n: _build_io_statement(n, StatementType.WRITE),
        "OPENSTATEMENT": lambda n: _build_io_statement(n, StatementType.OPEN),
        "OPEN_STATEMENT": lambda n: _build_io_statement(n, StatementType.OPEN),
        "CLOSESTATEMENT": lambda n: _build_io_statement(n, StatementType.CLOSE),
        "CLOSE_STATEMENT": lambda n: _build_io_statement(n, StatementType.CLOSE),
        "DISPLAYSTATEMENT": _build_display_statement,
        "DISPLAY_STATEMENT": _build_display_statement,
        "GOTOSTATEMENT": _build_goto_statement,
        "GOTO_STATEMENT": _build_goto_statement,
        "EXITSTATEMENT": lambda _: Statement(statement_type=StatementType.EXIT),
        "EXIT_STATEMENT": lambda _: Statement(statement_type=StatementType.EXIT),
        "STOPSTATEMENT": lambda _: Statement(statement_type=StatementType.STOP),
        "STOP_STATEMENT": lambda _: Statement(statement_type=StatementType.STOP),
        "GOBACKSTATEMENT": lambda _: Statement(statement_type=StatementType.GO_BACK),
        "GOBACK_STATEMENT": lambda _: Statement(statement_type=StatementType.GO_BACK),
        "CONTINUESTATEMENT": lambda _: Statement(statement_type=StatementType.CONTINUE),
        "CONTINUE_STATEMENT": lambda _: Statement(statement_type=StatementType.CONTINUE),
        "INITIALIZESTATEMENT": _build_initialize_statement,
        "INITIALIZE_STATEMENT": _build_initialize_statement,
        "SETSTATEMENT": _build_set_statement,
        "SET_STATEMENT": _build_set_statement,
        "SEARCHSTATEMENT": _build_search_statement,
        "SEARCH_STATEMENT": _build_search_statement,
        "STRINGSTATEMENT": _build_string_statement,
        "STRING_STATEMENT": _build_string_statement,
        "UNSTRINGSTATEMENT": _build_unstring_statement,
        "UNSTRING_STATEMENT": _build_unstring_statement,
        "INSPECTSTATEMENT": _build_inspect_statement,
        "INSPECT_STATEMENT": _build_inspect_statement,
        "ACCEPTSTATEMENT": _build_accept_statement,
        "ACCEPT_STATEMENT": _build_accept_statement,
    }

    builder = statement_builders.get(node.node_type)
    if builder:
        stmt = builder(node)
        if stmt:
            stmt.location = _create_source_location(node)
            return stmt

    logger.debug(f"Unsupported statement type: {node.node_type}")
    return None


def _build_call_statement(node: ParseNode) -> Statement:
    """Build CALL statement with full details."""
    # Extract program name from CALL literal (e.g., CALL 'CALCULATE-PENALTY')
    program_name = None
    literal_node = _find_child_node(node, "LITERAL")
    if literal_node:
        # Try NONNUMERICLITERAL child first
        nonnumeric = _find_child_value(literal_node, "NONNUMERICLITERAL")
        if nonnumeric:
            program_name = nonnumeric.strip("'\"")
        else:
            # Fall back to terminal node text (ANTLR stores the token text here)
            for child in literal_node.children:
                if child.text and child.text.strip("'\""):
                    program_name = child.text.strip("'\"")
                    break

    # Extract USING parameters
    parameters: list[CallParameter] = []
    using_phrase = _find_child_node(node, "CALLUSINGPHRASE")
    if using_phrase:
        for using_param in _walk_nodes(using_phrase, {"CALLUSINGPARAMETER"}):
            param = _extract_call_parameter(using_param)
            if param:
                parameters.append(param)

    # Extract GIVING clause
    giving_name = None
    giving_phrase = _find_child_node(node, "CALLGIVINGPHRASE")
    if giving_phrase:
        identifier = _find_child_node(giving_phrase, "IDENTIFIER")
        giving_name = _extract_variable_name(identifier)

    # Build statement details
    call_details = CallStatement(
        name=f"CALL {program_name or 'UNKNOWN'}",
        target_program=program_name or "UNKNOWN",
        target_is_literal=True,
        using_phrase=CallUsingPhrase(parameters=parameters) if parameters else None,
        parameters=parameters,
        giving_phrase=CallGivingPhrase(giving_name=giving_name) if giving_name else None,
        returning=giving_name,
    )

    return Statement(
        statement_type=StatementType.CALL,
        target=program_name,
        call_details=call_details,
    )


def _extract_call_parameter(using_param: ParseNode) -> CallParameter | None:
    """Extract parameter from CALLUSINGPARAMETER node.

    ANTLR structure:
    CALLUSINGPARAMETER
        └─ CALLBYREFERENCEPHRASE
            └─ CALLBYREFERENCE
                └─ IDENTIFIER
                    └─ QUALIFIEDDATANAME
                        └─ ... DATANAME
    """
    param_type = ParameterType.BY_REFERENCE
    param_name = None

    # Check for BY REFERENCE (use walk to find nested DATANAME)
    by_ref = _find_child_node(using_param, "CALLBYREFERENCEPHRASE")
    if by_ref:
        param_type = ParameterType.BY_REFERENCE
        # Look for DATANAME node which contains the actual variable name
        dataname_nodes = _walk_nodes(by_ref, {"DATANAME"})
        if dataname_nodes:
            param_name = dataname_nodes[0].value

    # Check for BY VALUE
    by_val = _find_child_node(using_param, "CALLBYVALUEPHRASE")
    if by_val:
        param_type = ParameterType.BY_VALUE
        dataname_nodes = _walk_nodes(by_val, {"DATANAME"})
        if dataname_nodes:
            param_name = dataname_nodes[0].value

    # Check for BY CONTENT
    by_content = _find_child_node(using_param, "CALLBYCONTENTPHRASE")
    if by_content:
        param_type = ParameterType.BY_CONTENT
        dataname_nodes = _walk_nodes(by_content, {"DATANAME"})
        if dataname_nodes:
            param_name = dataname_nodes[0].value

    # Direct identifier (implied BY REFERENCE) - fallback
    if not param_name:
        dataname_nodes = _walk_nodes(using_param, {"DATANAME"})
        if dataname_nodes:
            param_name = dataname_nodes[0].value

    if param_name:
        return CallParameter(name=str(param_name), parameter_type=param_type)

    return None


def _build_perform_statement(node: ParseNode) -> Statement:
    """Build PERFORM statement with full details."""
    perform_type = PerformType.SIMPLE
    target_paragraph = None
    through_paragraph = None

    # Check for inline PERFORM
    inline_stmt = _find_child_node(node, "PERFORMINLINESTATEMENT")
    if inline_stmt:
        return _build_perform_inline(inline_stmt)

    # Procedure PERFORM
    perform_proc = _find_child_node(node, "PERFORMPROCEDURESTATEMENT")
    if perform_proc:
        procedure_names = list(_walk_nodes(perform_proc, {"PROCEDURENAME"}))
        if procedure_names:
            target_paragraph = str(procedure_names[0].value or "")

            # Check for THRU
            has_thru = _find_child_node(perform_proc, "THRU") or _find_child_node(
                perform_proc, "THROUGH"
            )
            if has_thru and len(procedure_names) > 1:
                perform_type = PerformType.SIMPLE  # Will be updated if TIMES/UNTIL
                through_paragraph = str(procedure_names[1].value or "")

        # Extract PERFORMTYPE
        perform_type_node = _find_child_node(perform_proc, "PERFORMTYPE")
        if perform_type_node:
            perform_type, times, until, varying = _extract_perform_type(perform_type_node)

            procedure_stmt = PerformProcedureStatement(
                target_paragraph=target_paragraph,
                through_paragraph=through_paragraph,
                perform_type=perform_type,
                times=times,
                until=until,
                varying=varying,
            )

            perform_details = PerformStatement(
                name=f"PERFORM {target_paragraph or 'UNKNOWN'}",
                perform_type=perform_type,
                procedure_statement=procedure_stmt,
                target_paragraph=target_paragraph,
                through_paragraph=through_paragraph,
            )

            return Statement(
                statement_type=StatementType.PERFORM,
                target=target_paragraph,
                perform_details=perform_details,
            )

    # Simple PERFORM
    perform_details = PerformStatement(
        name=f"PERFORM {target_paragraph or 'UNKNOWN'}",
        perform_type=PerformType.SIMPLE,
        target_paragraph=target_paragraph,
        through_paragraph=through_paragraph,
    )

    return Statement(
        statement_type=StatementType.PERFORM,
        target=target_paragraph,
        perform_details=perform_details,
    )


def _build_perform_inline(inline_node: ParseNode) -> Statement:
    """Build inline PERFORM statement."""
    perform_type = PerformType.SIMPLE
    times = None
    until = None
    varying = None
    inline_statements: list[Statement] = []

    # Extract PERFORMTYPE
    perform_type_node = _find_child_node(inline_node, "PERFORMTYPE")
    if perform_type_node:
        perform_type, times, until, varying = _extract_perform_type(perform_type_node)

    # Extract inline statements
    for stmt_node in _walk_nodes(inline_node, {"STATEMENT"}):
        for child in stmt_node.children:
            if isinstance(child, ParseNode):
                stmt = _build_statement(child)
                if stmt:
                    inline_statements.append(stmt)

    inline_stmt = PerformInlineStatement(
        perform_type=perform_type,
        times=times,
        until=until,
        varying=varying,
        statements=inline_statements,
    )

    perform_details = PerformStatement(
        name="PERFORM INLINE",
        perform_type=perform_type,
        inline_statement=inline_stmt,
        is_inline=True,
    )

    return Statement(
        statement_type=StatementType.PERFORM,
        perform_details=perform_details,
    )


def _extract_perform_type(
    perform_type_node: ParseNode,
) -> tuple[PerformType, PerformTimes | None, PerformUntil | None, PerformVarying | None]:
    """Extract PERFORM type details."""
    # TIMES
    perform_times = _find_child_node(perform_type_node, "PERFORMTIMES")
    if perform_times:
        int_literal = _find_child_node(perform_times, "INTEGERLITERAL")
        times_value = _extract_integer_literal_value(int_literal) if int_literal else None
        return PerformType.TIMES, PerformTimes(times_value=times_value), None, None

    # VARYING (check before UNTIL since VARYING contains UNTIL)
    perform_varying = _find_child_node(perform_type_node, "PERFORMVARYING")
    if perform_varying:
        varying_clause = _find_child_node(perform_varying, "PERFORMVARYINGCLAUSE")
        if varying_clause:
            varying_phrase = _find_child_node(varying_clause, "PERFORMVARYINGPHRASE")
            if varying_phrase:
                varying = _extract_varying_details(varying_phrase)
                return PerformType.VARYING, None, None, varying
        return PerformType.VARYING, None, None, None

    # UNTIL
    perform_until = _find_child_node(perform_type_node, "PERFORMUNTIL")
    if perform_until:
        is_test_before = True
        test_clause = _find_child_node(perform_until, "PERFORMTESTCLAUSE")
        if test_clause:
            is_test_before = _find_child_node(test_clause, "AFTER") is None

        condition = _find_child_node(perform_until, "CONDITION")
        condition_text = _extract_condition_text(condition) if condition else None

        until = PerformUntil(
            condition_text=condition_text,
            is_test_before=is_test_before,
        )
        return PerformType.UNTIL, None, until, None

    return PerformType.SIMPLE, None, None, None


def _extract_varying_details(varying_phrase: ParseNode) -> PerformVarying:
    """Extract VARYING phrase details."""
    varying_name = None
    from_value: Any = None
    by_value: Any = None
    until_text = None

    # Variable
    identifier = _find_child_node(varying_phrase, "IDENTIFIER")
    varying_name = _extract_variable_name(identifier)

    # FROM
    from_clause = _find_child_node(varying_phrase, "PERFORMFROM")
    if from_clause:
        literal = _find_child_node(from_clause, "LITERAL")
        if literal:
            from_value = _extract_literal_value(literal)
        else:
            from_id = _find_child_node(from_clause, "IDENTIFIER")
            from_value = _extract_variable_name(from_id)

    # BY
    by_clause = _find_child_node(varying_phrase, "PERFORMBY")
    if by_clause:
        literal = _find_child_node(by_clause, "LITERAL")
        if literal:
            by_value = _extract_literal_value(literal)
        else:
            by_id = _find_child_node(by_clause, "IDENTIFIER")
            by_value = _extract_variable_name(by_id)

    # UNTIL
    until_clause = _find_child_node(varying_phrase, "PERFORMUNTIL")
    if until_clause:
        condition = _find_child_node(until_clause, "CONDITION")
        if condition:
            until_text = _extract_condition_text(condition)

    return PerformVarying(
        varying_name=varying_name,
        from_value=from_value,
        by_value=by_value,
        until_text=until_text,
    )


def _build_if_statement(node: ParseNode) -> Statement:
    """Build IF statement."""
    condition_node = _find_child_node(node, "CONDITION")
    condition_text = _extract_condition_text(condition_node) if condition_node else ""

    then_statements: list[Statement] = []
    else_statements: list[Statement] = []

    # THEN statements — direct children only, same as _build_paragraph
    ifthen = _find_child_node(node, "IFTHEN")
    if ifthen:
        for stmt_node in ifthen.children:
            if not isinstance(stmt_node, ParseNode) or stmt_node.node_type != "STATEMENT":
                continue
            for child in stmt_node.children:
                if isinstance(child, ParseNode):
                    stmt = _build_statement(child)
                    if stmt:
                        then_statements.append(stmt)

    # ELSE statements — direct children only
    ifelse = _find_child_node(node, "IFELSE")
    if ifelse:
        for stmt_node in ifelse.children:
            if not isinstance(stmt_node, ParseNode) or stmt_node.node_type != "STATEMENT":
                continue
            for child in stmt_node.children:
                if isinstance(child, ParseNode):
                    stmt = _build_statement(child)
                    if stmt:
                        else_statements.append(stmt)

    if_details = IfStatement(
        name="IF",
        condition=condition_text,
        then_statements=then_statements,
        else_statements=else_statements,
    )

    return Statement(
        statement_type=StatementType.IF,
        if_details=if_details,
    )


def _build_evaluate_statement(node: ParseNode) -> Statement:
    """Build EVALUATE statement."""
    subjects: list[str] = []
    when_clauses: list[EvaluateWhen] = []
    when_other_statements: list[Statement] = []

    # Extract subjects
    subject_node = _find_child_node(node, "EVALUATESUBJECT")
    if subject_node:
        identifier = _find_child_node(subject_node, "IDENTIFIER")
        if identifier:
            subjects.append(_extract_variable_name(identifier) or "")

    # Extract WHEN clauses
    for when_node in _walk_nodes(node, {"EVALUATEWHENPHRASE"}):
        condition_texts: list[str] = []
        statements: list[Statement] = []

        # Condition
        condition = _find_child_node(when_node, "EVALUATEWHEN")
        if condition:
            condition_texts.append(_extract_condition_text(condition))

        # Statements
        for stmt_node in _walk_nodes(when_node, {"STATEMENT"}):
            for child in stmt_node.children:
                if isinstance(child, ParseNode):
                    stmt = _build_statement(child)
                    if stmt:
                        statements.append(stmt)

        when_clauses.append(
            EvaluateWhen(
                condition_texts=condition_texts,
                statements=statements,
            )
        )

    # WHEN OTHER
    when_other = _find_child_node(node, "EVALUATEWHENOTHER")
    if when_other:
        for stmt_node in _walk_nodes(when_other, {"STATEMENT"}):
            for child in stmt_node.children:
                if isinstance(child, ParseNode):
                    stmt = _build_statement(child)
                    if stmt:
                        when_other_statements.append(stmt)

    evaluate_details = EvaluateStatement(
        name="EVALUATE",
        subjects=subjects,
        when_clauses=when_clauses,
        when_other_statements=when_other_statements,
    )

    return Statement(
        statement_type=StatementType.EVALUATE,
        evaluate_details=evaluate_details,
    )


def _build_move_statement(node: ParseNode) -> Statement:  # noqa: PLR0912
    """Build MOVE statement."""
    source = None
    targets: list[str] = []
    source_is_literal = False

    # Handle MOVETOSTATEMENT structure (MOVE x TO y z ...)
    move_to_stmt = _find_child_node(node, "MOVETOSTATEMENT")
    if move_to_stmt:
        # Extract source from MOVETOSENDINGAREA
        sending_area = _find_child_node(move_to_stmt, "MOVETOSENDINGAREA")
        if sending_area:
            # Check for identifier
            for identifier in _walk_nodes(sending_area, {"IDENTIFIER"}):
                source = _extract_variable_name(identifier)
                break
            # Check for literal
            if not source:
                for literal in _walk_nodes(sending_area, {"LITERAL"}):
                    lit_value = _extract_literal_value(literal)
                    if lit_value is not None:
                        source = str(lit_value)
                        source_is_literal = True
                    break
                # Check for figurative constant
                if not source:
                    for figurative in _walk_nodes(sending_area, {"FIGURATIVECONSTANT"}):
                        fig_value = _extract_figurative_constant(figurative)
                        if fig_value is not None:
                            source = str(fig_value)
                            source_is_literal = True
                        break

        # Extract targets — IDENTIFIER nodes that follow the TO terminal
        found_to = False
        for child in move_to_stmt.children:
            if isinstance(child, ParseNode):
                if child.node_type == "TERMINALNODEIMPL" and (child.text or "").strip() == "TO":
                    found_to = True
                elif found_to and child.node_type == "IDENTIFIER":
                    target = _extract_variable_name(child)
                    if target:
                        targets.append(target)

    # Fallback: Handle MOVECORRESPONDINGSTATEMENT or other MOVE variants
    if not source and not targets:
        move_corr = _find_child_node(node, "MOVECORRESPONDINGSTATEMENT")
        if move_corr:
            identifiers = list(_walk_nodes(move_corr, {"IDENTIFIER"}))
            if len(identifiers) >= 2:
                source = _extract_variable_name(identifiers[0])
                targets = [_extract_variable_name(identifiers[1]) or ""]

    move_details = MoveStatement(
        name="MOVE",
        source=source or "",
        targets=targets,
        source_is_literal=source_is_literal,
    )

    return Statement(
        statement_type=StatementType.MOVE,
        operands=[source or "", *targets],
        move_details=move_details,
    )


def _build_compute_statement(node: ParseNode) -> Statement:
    """Build COMPUTE statement."""
    targets: list[str] = []
    expression = ""

    # Extract targets
    for identifier in _walk_nodes(node, {"IDENTIFIER"}):
        target = _extract_variable_name(identifier)
        if target:
            targets.append(target)
            break  # First identifier is the target

    # Extract expression text
    arithmetic = _find_child_node(node, "ARITHMETICEXPRESSION")
    if arithmetic:
        expression = _extract_condition_text(arithmetic)

    compute_details = ComputeStatement(
        name="COMPUTE",
        targets=targets,
        expression=expression,
    )

    return Statement(
        statement_type=StatementType.COMPUTE,
        operands=targets,
        compute_details=compute_details,
    )


def _build_arithmetic_statement(node: ParseNode, stmt_type: StatementType) -> Statement:
    """Build arithmetic statement (ADD, SUBTRACT, MULTIPLY, DIVIDE)."""
    operands: list[str] = []

    for identifier in _walk_nodes(node, {"IDENTIFIER"}):
        var_name = _extract_variable_name(identifier)
        if var_name:
            operands.append(var_name)

    for literal in _walk_nodes(node, {"LITERAL"}):
        val = _extract_literal_value(literal)
        if val is not None:
            operands.append(str(val))

    return Statement(
        statement_type=stmt_type,
        operands=operands,
    )


def _build_io_statement(node: ParseNode, stmt_type: StatementType) -> Statement:
    """Build I/O statement (READ, WRITE, OPEN, CLOSE)."""
    target = _find_child_value(node, "FILENAME")
    if not target:
        identifier = _find_child_node(node, "IDENTIFIER")
        target = _extract_variable_name(identifier)

    return Statement(
        statement_type=stmt_type,
        target=target,
    )


def _build_display_statement(node: ParseNode) -> Statement:
    """Build DISPLAY statement."""
    operands: list[str] = []

    for identifier in _walk_nodes(node, {"IDENTIFIER"}):
        var_name = _extract_variable_name(identifier)
        if var_name:
            operands.append(var_name)

    for literal in _walk_nodes(node, {"LITERAL"}):
        val = _extract_literal_value(literal)
        if val is not None:
            operands.append(str(val))

    return Statement(
        statement_type=StatementType.DISPLAY,
        operands=operands,
    )


def _build_goto_statement(node: ParseNode) -> Statement:
    """Build GO TO statement."""
    target = _find_child_value(node, "PROCEDURENAME")

    return Statement(
        statement_type=StatementType.GO_TO,
        target=target,
    )


def _build_initialize_statement(node: ParseNode) -> Statement:
    """Build INITIALIZE statement."""
    target = _extract_variable_name(_find_child_node(node, "IDENTIFIER"))

    return Statement(
        statement_type=StatementType.INITIALIZE,
        target=target,
    )


def _build_set_statement(node: ParseNode) -> Statement:
    """Build SET statement."""
    target = _extract_variable_name(_find_child_node(node, "IDENTIFIER"))

    return Statement(
        statement_type=StatementType.SET,
        target=target,
    )


def _build_search_statement(node: ParseNode) -> Statement:
    """Build SEARCH statement."""
    target = _extract_variable_name(_find_child_node(node, "IDENTIFIER"))

    return Statement(
        statement_type=StatementType.SEARCH,
        target=target,
    )


def _build_string_statement(node: ParseNode) -> Statement:
    """Build STRING statement."""
    target = _extract_variable_name(_find_child_node(node, "IDENTIFIER"))

    return Statement(
        statement_type=StatementType.STRING,
        target=target,
    )


def _build_unstring_statement(node: ParseNode) -> Statement:
    """Build UNSTRING statement."""
    source = _extract_variable_name(_find_child_node(node, "IDENTIFIER"))

    return Statement(
        statement_type=StatementType.UNSTRING,
        target=source,
    )


def _build_inspect_statement(node: ParseNode) -> Statement:
    """Build INSPECT statement."""
    target = _extract_variable_name(_find_child_node(node, "IDENTIFIER"))

    return Statement(
        statement_type=StatementType.INSPECT,
        target=target,
    )


def _build_accept_statement(node: ParseNode) -> Statement:
    """Build ACCEPT statement."""
    target = _extract_variable_name(_find_child_node(node, "IDENTIFIER"))

    return Statement(
        statement_type=StatementType.ACCEPT,
        target=target,
    )


# =============================================================================
# Utility Functions
# =============================================================================


def _extract_external_calls(program_unit: ProgramUnit) -> list[str]:
    """Extract external program calls from procedure division."""
    calls: list[str] = []

    if program_unit.procedure_division:
        for call_stmt in program_unit.procedure_division.call_statements:
            if call_stmt.target_program and call_stmt.target_program not in calls:
                calls.append(call_stmt.target_program)

    return calls


# =============================================================================
# Public API
# =============================================================================


def build_asg_with_preprocessing(
    file_path: str,
    copybook_directories: list[str] | None = None,
) -> Program:
    """Build ASG from COBOL source file with COPY/REPLACE preprocessing.

    Reads the file, then delegates to build_asg_from_source_with_preprocessing.
    The file's parent directory is always prepended to copybook_directories so
    that relative COPY statements resolve correctly.

    Args:
        file_path: Path to COBOL source file
        copybook_directories: Additional directories to search for copybooks.
            The source file's directory is always searched first.

    Returns:
        Program object containing the full ASG, with copybook_usages and
        any preprocessing errors stored in program.errors.

    Raises:
        ASGBuilderError: If file not found or parsing fails
    """
    path = Path(file_path)
    if not path.exists():
        raise ASGBuilderError(f"File not found: {file_path}")

    source_code = path.read_text(encoding="utf-8", errors="replace")
    # Prepend the file's own directory so relative COPY statements resolve
    dirs = [str(path.parent), *(copybook_directories or [])]
    return build_asg_from_source_with_preprocessing(
        source_code,
        source_file=str(path.absolute()),
        copybook_directories=dirs,
    )


def build_asg_from_source_with_preprocessing(
    source_code: str,
    source_file: str = "inline",
    copybook_directories: list[str] | None = None,
) -> Program:
    """Build ASG from COBOL source string with COPY/REPLACE preprocessing.

    Args:
        source_code: COBOL source code string
        source_file: Optional source file name for metadata
        copybook_directories: Directories to search for copybooks

    Returns:
        Program object containing the full ASG, with copybook_usages and
        any preprocessing errors stored in program.errors.
    """
    # Configure preprocessor
    copy_dirs = [Path(d) for d in (copybook_directories or [])]
    config = PreprocessorConfig(
        copybook_directories=copy_dirs,
        expand_copy_statements=True,
        process_replace_directives=True,
    )

    # Preprocess source
    preprocessor = CobolPreprocessor(config)
    preprocessed: PreprocessedSource = preprocessor.process_source(source_code)

    # Parse the preprocessed source
    parse_tree, _comments, id_metadata = parse_cobol(preprocessed.source)

    # Build ASG
    program = build_asg(parse_tree, source_file, id_metadata)

    # Store preprocessing errors in program.errors
    if preprocessed.errors:
        program.errors.extend(preprocessed.errors)

    # Add copybook usage information
    if preprocessed.copybook_usages:
        program.copybook_usages = [
            {
                "copybook_name": u.copybook_name,
                "source_line": u.source_line,
                "resolved_path": str(u.resolved_path) if u.resolved_path else None,
                "is_resolved": u.is_resolved,
            }
            for u in preprocessed.copybook_usages
        ]

    return program


# =============================================================================
# Cross-Reference Resolution
# =============================================================================


def _build_symbol_table(
    data_division: DataDivision | None,
) -> dict[str, list[DataDescriptionEntry]]:
    """Build a symbol table mapping variable names to their DataDescriptionEntry objects.

    Uses a multi-map (name → list of entries) to correctly handle programs where
    the same field name appears in multiple group items.

    Args:
        data_division: The data division containing all data definitions

    Returns:
        Dictionary mapping uppercase variable names to all matching entries
    """
    symbol_table: dict[str, list[DataDescriptionEntry]] = {}

    def add_entries(entries: list[DataDescriptionEntry]) -> None:
        for entry in entries:
            if entry.name and entry.name.upper() != "FILLER":
                key = entry.name.upper()
                if key not in symbol_table:
                    symbol_table[key] = []
                symbol_table[key].append(entry)
            # Recursively add children
            if entry.children:
                add_entries(entry.children)

    if data_division:
        if data_division.working_storage:
            add_entries(data_division.working_storage.entries)
        if data_division.linkage_section:
            add_entries(data_division.linkage_section.entries)
        if data_division.local_storage:
            add_entries(data_division.local_storage.entries)
        if data_division.file_section:
            for fd in data_division.file_section.file_descriptions:
                add_entries(fd.record_entries)

    return symbol_table


class _VariableReference:
    """Internal class to track variable references with read/write info."""

    def __init__(
        self,
        name: str,
        location: SourceLocation | None,
        is_read: bool = True,
        is_write: bool = False,
    ):
        self.name = name
        self.location = location
        self.is_read = is_read
        self.is_write = is_write


def _extract_refs_from_move(stmt: Statement) -> list[_VariableReference]:
    """Extract variable references from MOVE statement."""
    refs: list[_VariableReference] = []
    if stmt.move_details:
        if stmt.move_details.source:
            refs.append(
                _VariableReference(
                    stmt.move_details.source, stmt.location, is_read=True, is_write=False
                )
            )
        for target in stmt.move_details.targets:
            refs.append(_VariableReference(target, stmt.location, is_read=False, is_write=True))
    return refs


def _extract_refs_from_compute(stmt: Statement) -> list[_VariableReference]:
    """Extract variable references from COMPUTE statement."""
    refs: list[_VariableReference] = []
    if stmt.compute_details:
        for target in stmt.compute_details.targets:
            refs.append(_VariableReference(target, stmt.location, is_read=False, is_write=True))
        if stmt.compute_details.expression:
            expr_vars = _extract_identifiers_from_expression(stmt.compute_details.expression)
            for var in expr_vars:
                refs.append(_VariableReference(var, stmt.location, is_read=True, is_write=False))
    return refs


def _extract_refs_from_arithmetic(stmt: Statement) -> list[_VariableReference]:
    """Extract variable references from ADD/SUBTRACT/MULTIPLY/DIVIDE statements."""
    refs: list[_VariableReference] = []
    if stmt.operands:
        for operand in stmt.operands:
            refs.append(_VariableReference(operand, stmt.location, is_read=True, is_write=False))
    if stmt.target:
        # Target is both read and written (e.g., ADD A TO B means B = B + A)
        refs.append(_VariableReference(stmt.target, stmt.location, is_read=True, is_write=True))
    return refs


def _extract_refs_from_call(stmt: Statement) -> list[_VariableReference]:
    """Extract variable references from CALL statement."""
    refs: list[_VariableReference] = []
    if stmt.call_details:
        if stmt.call_details.using_phrase:
            for param in stmt.call_details.using_phrase.parameters:
                if param.name:
                    is_write = param.parameter_type == ParameterType.BY_REFERENCE
                    refs.append(
                        _VariableReference(
                            param.name, stmt.location, is_read=True, is_write=is_write
                        )
                    )
        if stmt.call_details.giving_phrase and stmt.call_details.giving_phrase.giving_name:
            refs.append(
                _VariableReference(
                    stmt.call_details.giving_phrase.giving_name,
                    stmt.location,
                    is_read=False,
                    is_write=True,
                )
            )
    return refs


def _extract_refs_from_if(
    stmt: Statement, paragraph_name: str, section_name: str | None
) -> list[_VariableReference]:
    """Extract variable references from IF statement."""
    refs: list[_VariableReference] = []
    if stmt.if_details:
        if stmt.if_details.condition:
            cond_vars = _extract_identifiers_from_expression(stmt.if_details.condition)
            for var in cond_vars:
                refs.append(_VariableReference(var, stmt.location, is_read=True, is_write=False))
        for then_stmt in stmt.if_details.then_statements:
            refs.extend(
                _extract_variable_references_from_statement(then_stmt, paragraph_name, section_name)
            )
        for else_stmt in stmt.if_details.else_statements:
            refs.extend(
                _extract_variable_references_from_statement(else_stmt, paragraph_name, section_name)
            )
    return refs


def _extract_refs_from_evaluate(
    stmt: Statement, paragraph_name: str, section_name: str | None
) -> list[_VariableReference]:
    """Extract variable references from EVALUATE statement."""
    refs: list[_VariableReference] = []
    if stmt.evaluate_details:
        for subject in stmt.evaluate_details.subjects:
            subj_vars = _extract_identifiers_from_expression(subject)
            for var in subj_vars:
                refs.append(_VariableReference(var, stmt.location, is_read=True, is_write=False))
        for when_clause in stmt.evaluate_details.when_clauses:
            for when_stmt in when_clause.statements:
                refs.extend(
                    _extract_variable_references_from_statement(
                        when_stmt, paragraph_name, section_name
                    )
                )
    return refs


def _extract_refs_from_io(stmt: Statement) -> list[_VariableReference]:
    """Extract variable references from I/O statements (READ, WRITE, DISPLAY)."""
    refs: list[_VariableReference] = []
    if stmt.statement_type == StatementType.READ and stmt.target:
        refs.append(_VariableReference(stmt.target, stmt.location, is_read=False, is_write=True))
    elif stmt.statement_type == StatementType.WRITE and stmt.target:
        refs.append(_VariableReference(stmt.target, stmt.location, is_read=True, is_write=False))
    elif stmt.statement_type == StatementType.DISPLAY and stmt.operands:
        for operand in stmt.operands:
            if operand and not operand.startswith("'") and not operand.startswith('"'):
                refs.append(
                    _VariableReference(operand, stmt.location, is_read=True, is_write=False)
                )
    return refs


def _extract_refs_from_data_manipulation(stmt: Statement) -> list[_VariableReference]:
    """Extract refs from SET, INITIALIZE, STRING, UNSTRING statements."""
    refs: list[_VariableReference] = []
    if stmt.statement_type == StatementType.SET:
        if stmt.target:
            refs.append(
                _VariableReference(stmt.target, stmt.location, is_read=False, is_write=True)
            )
        if stmt.operands:
            for operand in stmt.operands:
                refs.append(
                    _VariableReference(operand, stmt.location, is_read=True, is_write=False)
                )
    elif stmt.statement_type == StatementType.INITIALIZE and stmt.target:
        refs.append(_VariableReference(stmt.target, stmt.location, is_read=False, is_write=True))
    elif stmt.statement_type in (StatementType.STRING, StatementType.UNSTRING):
        if stmt.target:
            refs.append(
                _VariableReference(stmt.target, stmt.location, is_read=False, is_write=True)
            )
        if stmt.operands:
            for operand in stmt.operands:
                refs.append(
                    _VariableReference(operand, stmt.location, is_read=True, is_write=False)
                )
    return refs


def _extract_variable_references_from_statement(
    stmt: Statement,
    paragraph_name: str,
    section_name: str | None = None,
) -> list[_VariableReference]:
    """Extract all variable references from a statement.

    Args:
        stmt: The statement to analyze
        paragraph_name: Name of containing paragraph
        section_name: Name of containing section (if any)

    Returns:
        List of _VariableReference objects
    """
    stmt_type = stmt.statement_type

    # Simple handlers (no context needed)
    simple_handlers = {
        StatementType.MOVE: _extract_refs_from_move,
        StatementType.COMPUTE: _extract_refs_from_compute,
        StatementType.CALL: _extract_refs_from_call,
        StatementType.ADD: _extract_refs_from_arithmetic,
        StatementType.SUBTRACT: _extract_refs_from_arithmetic,
        StatementType.MULTIPLY: _extract_refs_from_arithmetic,
        StatementType.DIVIDE: _extract_refs_from_arithmetic,
        StatementType.READ: _extract_refs_from_io,
        StatementType.WRITE: _extract_refs_from_io,
        StatementType.DISPLAY: _extract_refs_from_io,
        StatementType.SET: _extract_refs_from_data_manipulation,
        StatementType.INITIALIZE: _extract_refs_from_data_manipulation,
        StatementType.STRING: _extract_refs_from_data_manipulation,
        StatementType.UNSTRING: _extract_refs_from_data_manipulation,
    }

    # Check simple handlers first
    handler = simple_handlers.get(stmt_type)
    if handler is not None:
        return handler(stmt)

    # Context-dependent handlers (need paragraph/section names for recursion)
    if stmt_type == StatementType.IF:
        return _extract_refs_from_if(stmt, paragraph_name, section_name)
    if stmt_type == StatementType.EVALUATE:
        return _extract_refs_from_evaluate(stmt, paragraph_name, section_name)

    # Recurse into inline PERFORM body statements
    if stmt_type == StatementType.PERFORM:
        refs: list[_VariableReference] = []
        if stmt.perform_details and stmt.perform_details.inline_statement:
            for nested in stmt.perform_details.inline_statement.statements:
                refs.extend(
                    _extract_variable_references_from_statement(
                        nested, paragraph_name, section_name
                    )
                )
        return refs

    return []


def _extract_identifiers_from_expression(expr: str) -> list[str]:
    """Extract potential variable identifiers from an expression string.

    Args:
        expr: Expression string that may contain variable references

    Returns:
        List of potential variable names (uppercase)
    """
    # COBOL identifiers: start with letter, contain letters, digits, hyphens
    # But not literals (quoted strings or numbers)
    identifiers: list[str] = []

    # Remove string literals first
    expr_no_strings = re.sub(r"'[^']*'", "", expr)
    expr_no_strings = re.sub(r'"[^"]*"', "", expr_no_strings)

    # Find all potential COBOL identifiers
    # Pattern: starts with letter, contains letters/digits/hyphens
    pattern = r"\b([A-Za-z][A-Za-z0-9-]*)\b"
    matches = re.findall(pattern, expr_no_strings)

    # Filter out COBOL reserved words and operators
    reserved_words = {
        "AND",
        "OR",
        "NOT",
        "EQUAL",
        "EQUALS",
        "LESS",
        "GREATER",
        "THAN",
        "TO",
        "OF",
        "IN",
        "TRUE",
        "FALSE",
        "ZERO",
        "ZEROS",
        "ZEROES",
        "SPACE",
        "SPACES",
        "HIGH-VALUE",
        "HIGH-VALUES",
        "LOW-VALUE",
        "LOW-VALUES",
        "QUOTE",
        "QUOTES",
        "NULL",
        "NULLS",
        "ALL",
        "ANY",
    }

    for match in matches:
        upper_match = match.upper()
        if upper_match not in reserved_words:
            identifiers.append(upper_match)

    return identifiers


def _resolve_cross_references(
    data_division: DataDivision | None,
    proc_division: ProcedureDivision | None,
) -> None:
    """Resolve cross-references between procedure statements and data items.

    This mutates the DataDescriptionEntry objects to add their `calls` list,
    tracking all places where each variable is referenced.

    Also resolves paragraph/section cross-references (who performs whom).

    Args:
        data_division: The data division containing all data definitions
        proc_division: The procedure division containing all statements
    """
    # Resolve paragraph cross-references (can work without data division)
    if proc_division:
        _resolve_paragraph_cross_references(proc_division)

    # Data item cross-references require both divisions
    if not data_division or not proc_division:
        return

    # Build symbol table
    symbol_table = _build_symbol_table(data_division)

    # Collect all variable references from procedure division
    all_refs: list[_VariableReference] = []

    for para in proc_division.paragraphs:
        for stmt in para.statements:
            refs = _extract_variable_references_from_statement(
                stmt, para.paragraph_name or para.name or "UNKNOWN"
            )
            all_refs.extend(refs)

    # Also check sections
    for section in proc_division.sections:
        for para in section.paragraphs:
            for stmt in para.statements:
                refs = _extract_variable_references_from_statement(
                    stmt, para.paragraph_name or para.name or "UNKNOWN", section.name
                )
                all_refs.extend(refs)

    # Resolve references to data entries
    for ref in all_refs:
        # Normalize name for lookup, extracting qualifier (OF/IN) separately
        normalized_name = ref.name.upper().strip()
        qualifier: str | None = None

        if " OF " in normalized_name:
            parts = normalized_name.split(" OF ", 1)
            normalized_name = parts[0].strip()
            qualifier = parts[1].strip()
        elif " IN " in normalized_name:
            parts = normalized_name.split(" IN ", 1)
            normalized_name = parts[0].strip()
            qualifier = parts[1].strip()

        matches = symbol_table.get(normalized_name, [])
        if not matches:
            continue

        # When multiple entries share the same name, use the qualifier (parent
        # group name) to pick the right one.  If no qualifier is present, record
        # the reference on all matching entries (conservative — same behaviour as
        # ProLeap when the reference is unqualified).
        if len(matches) > 1 and qualifier:
            narrowed = [e for e in matches if e.parent_name and e.parent_name.upper() == qualifier]
            if narrowed:
                matches = narrowed

        for entry in matches:
            call = DataDescriptionEntryCall(
                name=ref.name,
                call_type=CallType.DATA_DESCRIPTION_ENTRY_CALL,
                location=ref.location,
                is_read=ref.is_read,
                is_write=ref.is_write,
            )
            entry.calls.append(call)


def _resolve_paragraph_cross_references(proc_division: ProcedureDivision) -> None:
    """Resolve paragraph and section cross-references.

    Tracks who performs each paragraph/section by populating the `calls` list
    on Paragraph and Section objects.

    Args:
        proc_division: The procedure division to analyze
    """
    # Build paragraph lookup table: name -> Paragraph
    paragraph_table: dict[str, Paragraph] = {}
    section_table: dict[str, Section] = {}

    # Index top-level paragraphs
    for para in proc_division.paragraphs:
        para_name = (para.paragraph_name or para.name or "").upper()
        if para_name:
            paragraph_table[para_name] = para

    # Index sections and their paragraphs
    for section in proc_division.sections:
        section_name = (section.name or "").upper()
        if section_name:
            section_table[section_name] = section
        for para in section.paragraphs:
            para_name = (para.paragraph_name or para.name or "").upper()
            if para_name:
                paragraph_table[para_name] = para

    # Collect all PERFORM statements and track who performs whom
    _collect_perform_references(
        proc_division.paragraphs,
        None,  # No section for top-level paragraphs
        paragraph_table,
        section_table,
    )

    for section in proc_division.sections:
        _collect_perform_references(
            section.paragraphs,
            section,
            paragraph_table,
            section_table,
        )

    # Update called_by_count for all paragraphs and sections
    for para in proc_division.paragraphs:
        para.called_by_count = len(para.called_by)
    for section in proc_division.sections:
        section.called_by_count = len(section.called_by)
        for para in section.paragraphs:
            para.called_by_count = len(para.called_by)


def _collect_perform_references(
    paragraphs: list[Paragraph],
    calling_section: Section | None,
    paragraph_table: dict[str, Paragraph],
    section_table: dict[str, Section],
) -> None:
    """Collect PERFORM references from paragraphs and update cross-reference lists.

    Args:
        paragraphs: List of paragraphs to scan
        calling_section: The Section object containing the paragraphs (if any)
        paragraph_table: Lookup table for paragraphs
        section_table: Lookup table for sections
    """
    for para in paragraphs:
        caller_name = para.paragraph_name or para.name or "UNKNOWN"

        for stmt in para.statements:
            _process_perform_statement(
                stmt,
                caller_name,
                para,
                calling_section,
                paragraph_table,
                section_table,
            )


def _add_paragraph_call(
    target_para: Paragraph,
    caller_name: str,
    location: SourceLocation | None,
    is_thru: bool = False,
) -> None:
    """Add a PERFORM call reference to a paragraph."""
    caller_upper = caller_name.upper()
    if caller_upper not in target_para.called_by:
        target_para.called_by.append(caller_upper)

    label = "PERFORM THRU from" if is_thru else "PERFORM from"
    proc_call = ProcedureCall(
        name=f"{label} {caller_name}",
        call_type=CallType.PROCEDURE_CALL,
        location=location,
        paragraph_name=caller_name,
    )
    target_para.calls.append(proc_call)


def _add_section_call(
    target_section: Section,
    caller_name: str,
    location: SourceLocation | None,
    is_thru: bool = False,
) -> None:
    """Add a PERFORM call reference to a section."""
    caller_upper = caller_name.upper()
    if caller_upper not in target_section.called_by:
        target_section.called_by.append(caller_upper)

    label = "PERFORM THRU from" if is_thru else "PERFORM from"
    section_call = SectionCall(
        name=f"{label} {caller_name}",
        call_type=CallType.SECTION_CALL,
        location=location,
        section_name=caller_name,
    )
    target_section.calls.append(section_call)


def _process_perform_target(
    stmt: Statement,
    caller_name: str,
    calling_para: Paragraph,
    calling_section: Section | None,
    paragraph_table: dict[str, Paragraph],
    section_table: dict[str, Section],
) -> None:
    """Process the target of a PERFORM statement."""
    target = None
    through_target = None

    if stmt.perform_details:
        target = stmt.perform_details.target_paragraph
        through_target = stmt.perform_details.through_paragraph
    elif stmt.target:
        target = stmt.target

    if not target:
        return

    target_upper = target.upper()

    # Add to caller's calls_to list (paragraph)
    if target_upper not in calling_para.calls_to:
        calling_para.calls_to.append(target_upper)

    # Also add to caller section's calls_to list if applicable
    if calling_section and target_upper not in calling_section.calls_to:
        calling_section.calls_to.append(target_upper)

    # Check if target is a paragraph
    if target_upper in paragraph_table:
        _add_paragraph_call(paragraph_table[target_upper], caller_name, stmt.location)
    # Check if target is a section
    elif target_upper in section_table:
        _add_section_call(section_table[target_upper], caller_name, stmt.location)

    # Handle THRU clause for paragraphs
    if through_target:
        through_upper = through_target.upper()
        if through_upper in paragraph_table:
            _add_paragraph_call(
                paragraph_table[through_upper], caller_name, stmt.location, is_thru=True
            )
        elif through_upper in section_table:
            _add_section_call(
                section_table[through_upper], caller_name, stmt.location, is_thru=True
            )


def _process_perform_statement(
    stmt: Statement,
    caller_name: str,
    calling_para: Paragraph,
    calling_section: Section | None,
    paragraph_table: dict[str, Paragraph],
    section_table: dict[str, Section],
) -> None:
    """Process a single statement for PERFORM references.

    Also recursively processes nested statements (IF/EVALUATE).

    Args:
        stmt: Statement to process
        caller_name: Name of the calling paragraph
        calling_para: The Paragraph object making the call
        calling_section: The Section object containing the caller (if any)
        paragraph_table: Lookup table for paragraphs
        section_table: Lookup table for sections
    """
    if stmt.statement_type == StatementType.PERFORM:
        _process_perform_target(
            stmt, caller_name, calling_para, calling_section, paragraph_table, section_table
        )
        # Recurse into inline PERFORM body statements
        if stmt.perform_details and stmt.perform_details.inline_statement:
            for nested in stmt.perform_details.inline_statement.statements:
                _process_perform_statement(
                    nested,
                    caller_name,
                    calling_para,
                    calling_section,
                    paragraph_table,
                    section_table,
                )
        return

    # Recursively process nested statements in IF
    if stmt.statement_type == StatementType.IF and stmt.if_details:
        for nested in stmt.if_details.then_statements + stmt.if_details.else_statements:
            _process_perform_statement(
                nested, caller_name, calling_para, calling_section, paragraph_table, section_table
            )
        return

    # Recursively process nested statements in EVALUATE
    if stmt.statement_type == StatementType.EVALUATE and stmt.evaluate_details:
        for when_clause in stmt.evaluate_details.when_clauses:
            for nested in when_clause.statements:
                _process_perform_statement(
                    nested,
                    caller_name,
                    calling_para,
                    calling_section,
                    paragraph_table,
                    section_table,
                )
