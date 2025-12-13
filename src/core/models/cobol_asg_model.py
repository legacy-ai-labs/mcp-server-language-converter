"""
COBOL Abstract Semantic Graph (ASG) Data Model

This module defines the Python data model for COBOL ASG, designed to be compatible
with common COBOL ASG structures while being Python-native and suitable for JSON serialization.

The ASG captures semantic information about COBOL programs including:
- Program structure (divisions, sections, paragraphs)
- Data definitions with resolved references
- Procedure statements with semantic context
- Inter-program relationships (CALL targets)
- Symbol tables and cross-references

Usage:
    from src.core.models.cobol_asg_model import Program, CompilationUnit, DataDescriptionEntry

    # Build ASG from parsed COBOL
    program = Program(
        source_file="CUSTOMER-MGMT.cbl",
        compilation_units=[...]
    )

    # Serialize to JSON
    asg_json = program.model_dump()
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class DataDescriptionEntryType(str, Enum):
    """Types of data description entries in COBOL."""

    GROUP = "GROUP"  # Level 01-49 with subordinate items
    ELEMENTARY = "ELEMENTARY"  # Level 01-49 without subordinate items (has PICTURE)
    CONDITION = "CONDITION"  # Level 88 condition names
    RENAME = "RENAME"  # Level 66 renames
    SCALAR = "SCALAR"  # Level 77 independent items


class StatementType(str, Enum):
    """COBOL statement types (procedure division verbs)."""

    ACCEPT = "ACCEPT"
    ADD = "ADD"
    ALTER = "ALTER"
    CALL = "CALL"
    CANCEL = "CANCEL"
    CLOSE = "CLOSE"
    COMPUTE = "COMPUTE"
    CONTINUE = "CONTINUE"
    DELETE = "DELETE"
    DISABLE = "DISABLE"
    DISPLAY = "DISPLAY"
    DIVIDE = "DIVIDE"
    ENABLE = "ENABLE"
    ENTRY = "ENTRY"
    EVALUATE = "EVALUATE"
    EXEC_CICS = "EXEC_CICS"
    EXEC_SQL = "EXEC_SQL"
    EXEC_SQLIMS = "EXEC_SQLIMS"
    EXHIBIT = "EXHIBIT"
    EXIT = "EXIT"
    GENERATE = "GENERATE"
    GO_BACK = "GO_BACK"
    GO_TO = "GO_TO"
    IF = "IF"
    INITIALIZE = "INITIALIZE"
    INITIATE = "INITIATE"
    INSPECT = "INSPECT"
    MERGE = "MERGE"
    MOVE = "MOVE"
    MULTIPLY = "MULTIPLY"
    OPEN = "OPEN"
    PERFORM = "PERFORM"
    PURGE = "PURGE"
    READ = "READ"
    RECEIVE = "RECEIVE"
    RELEASE = "RELEASE"
    RETURN = "RETURN"
    REWRITE = "REWRITE"
    SEARCH = "SEARCH"
    SEND = "SEND"
    SET = "SET"
    SORT = "SORT"
    START = "START"
    STOP = "STOP"
    STRING = "STRING"
    SUBTRACT = "SUBTRACT"
    TERMINATE = "TERMINATE"
    UNSTRING = "UNSTRING"
    USE = "USE"
    WRITE = "WRITE"


class UsageType(str, Enum):
    """COBOL USAGE clause types."""

    BINARY = "BINARY"
    BINARY_CHAR = "BINARY_CHAR"
    BINARY_SHORT = "BINARY_SHORT"
    BINARY_LONG = "BINARY_LONG"
    BINARY_DOUBLE = "BINARY_DOUBLE"
    BIT = "BIT"
    COMP = "COMP"
    COMP_1 = "COMP-1"
    COMP_2 = "COMP-2"
    COMP_3 = "COMP-3"
    COMP_4 = "COMP-4"
    COMP_5 = "COMP-5"
    COMPUTATIONAL = "COMPUTATIONAL"
    COMPUTATIONAL_1 = "COMPUTATIONAL-1"
    COMPUTATIONAL_2 = "COMPUTATIONAL-2"
    COMPUTATIONAL_3 = "COMPUTATIONAL-3"
    COMPUTATIONAL_4 = "COMPUTATIONAL-4"
    COMPUTATIONAL_5 = "COMPUTATIONAL-5"
    CONTROL_POINT = "CONTROL-POINT"
    DATE = "DATE"
    DISPLAY = "DISPLAY"
    DISPLAY_1 = "DISPLAY-1"
    DOUBLE = "DOUBLE"
    EVENT = "EVENT"
    FUNCTION_POINTER = "FUNCTION-POINTER"
    INDEX = "INDEX"
    KANJI = "KANJI"
    LOCK = "LOCK"
    NATIONAL = "NATIONAL"
    OBJECT = "OBJECT"
    PACKED_DECIMAL = "PACKED-DECIMAL"
    POINTER = "POINTER"
    POINTER_32 = "POINTER-32"
    PROCEDURE_POINTER = "PROCEDURE-POINTER"
    REAL = "REAL"
    SQL = "SQL"
    TASK = "TASK"


class CallType(str, Enum):
    """
    Types of calls/references in COBOL.

    Used for cross-reference tracking to identify what kind of element is being referenced.
    """

    DATA_DESCRIPTION_ENTRY_CALL = "DATA_DESCRIPTION_ENTRY_CALL"
    PROCEDURE_CALL = "PROCEDURE_CALL"  # Reference to paragraph
    SECTION_CALL = "SECTION_CALL"  # Reference to section
    FUNCTION_CALL = "FUNCTION_CALL"  # Intrinsic function
    SPECIAL_REGISTER_CALL = "SPECIAL_REGISTER_CALL"
    INDEX_CALL = "INDEX_CALL"
    TABLE_CALL = "TABLE_CALL"
    FILE_CONTROL_ENTRY_CALL = "FILE_CONTROL_ENTRY_CALL"
    ENVIRONMENT_CALL = "ENVIRONMENT_CALL"
    MNEMONIC_CALL = "MNEMONIC_CALL"
    REPORT_DESCRIPTION_CALL = "REPORT_DESCRIPTION_CALL"
    SCREEN_DESCRIPTION_ENTRY_CALL = "SCREEN_DESCRIPTION_ENTRY_CALL"
    COMMUNICATION_DESCRIPTION_ENTRY_CALL = "COMMUNICATION_DESCRIPTION_ENTRY_CALL"
    UNDEFINED_CALL = "UNDEFINED_CALL"


class PerformType(str, Enum):
    """COBOL PERFORM types."""

    SIMPLE = "SIMPLE"  # Plain PERFORM
    TIMES = "TIMES"  # PERFORM n TIMES
    UNTIL = "UNTIL"  # PERFORM UNTIL condition
    VARYING = "VARYING"  # PERFORM VARYING


class ValueStmtType(str, Enum):
    """Types of value statements/expressions."""

    LITERAL = "LITERAL"
    INTEGER_LITERAL = "INTEGER_LITERAL"
    BOOLEAN_LITERAL = "BOOLEAN_LITERAL"
    CALL_VALUE = "CALL_VALUE"  # Reference to data item/variable
    ARITHMETIC = "ARITHMETIC"
    CONDITION = "CONDITION"
    RELATION_CONDITION = "RELATION_CONDITION"
    TERMINAL = "TERMINAL"


class SynchronizedType(str, Enum):
    """COBOL SYNCHRONIZED clause types."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"


class CommonOwnLocalType(str, Enum):
    """COBOL COMMON/OWN/LOCAL clause types."""

    COMMON = "COMMON"
    OWN = "OWN"
    LOCAL = "LOCAL"


class AlignedType(str, Enum):
    """COBOL ALIGNED clause types."""

    ALIGNED = "ALIGNED"
    ANY_LENGTH = "ANY_LENGTH"


class SignType(str, Enum):
    """COBOL SIGN clause types."""

    LEADING = "LEADING"
    TRAILING = "TRAILING"
    LEADING_SEPARATE = "LEADING_SEPARATE"
    TRAILING_SEPARATE = "TRAILING_SEPARATE"


class FileOrganization(str, Enum):
    """COBOL file organization types."""

    SEQUENTIAL = "SEQUENTIAL"
    INDEXED = "INDEXED"
    RELATIVE = "RELATIVE"
    LINE_SEQUENTIAL = "LINE_SEQUENTIAL"


class FileAccessMode(str, Enum):
    """COBOL file access modes."""

    SEQUENTIAL = "SEQUENTIAL"
    RANDOM = "RANDOM"
    DYNAMIC = "DYNAMIC"


class ParameterType(str, Enum):
    """CALL statement parameter types."""

    BY_REFERENCE = "BY_REFERENCE"
    BY_CONTENT = "BY_CONTENT"
    BY_VALUE = "BY_VALUE"


# =============================================================================
# Source Location
# =============================================================================


class SourceLocation(BaseModel):
    """Source code location information."""

    line: int = Field(description="Line number (1-based)")
    column: int = Field(default=0, description="Column number (0-based)")
    end_line: int | None = Field(default=None, description="End line number")
    end_column: int | None = Field(default=None, description="End column number")


# =============================================================================
# Base ASG Element
# =============================================================================


class ASGElement(BaseModel):
    """Base class for all ASG elements."""

    name: str | None = Field(default=None, description="Element name")
    location: SourceLocation | None = Field(default=None, description="Source location")

    model_config = {"extra": "allow"}


# =============================================================================
# Call/Reference Model
# =============================================================================


class Call(BaseModel):
    """
    A reference/call to another element in COBOL code.

    This represents any reference from one part of the code to another,
    enabling bidirectional cross-reference tracking.
    """

    name: str = Field(description="The identifier being referenced")
    call_type: CallType = Field(description="Type of call/reference")
    location: SourceLocation | None = Field(default=None, description="Where the reference occurs")

    # Resolved target (filled during semantic analysis)
    target_qualified_name: str | None = Field(
        default=None, description="Qualified name of referenced element"
    )

    model_config = {"extra": "allow"}


class DataDescriptionEntryCall(Call):
    """Reference to a data description entry (variable)."""

    call_type: CallType = Field(default=CallType.DATA_DESCRIPTION_ENTRY_CALL)
    is_read: bool = Field(default=True, description="Whether this is a read access")
    is_write: bool = Field(default=False, description="Whether this is a write access")
    qualifiers: list[str] = Field(default_factory=list, description="Qualification chain")


class ProcedureCall(Call):
    """Reference to a paragraph."""

    call_type: CallType = Field(default=CallType.PROCEDURE_CALL)
    paragraph_name: str | None = Field(default=None)


class SectionCall(Call):
    """Reference to a section."""

    call_type: CallType = Field(default=CallType.SECTION_CALL)
    section_name: str | None = Field(default=None)


class FileControlEntryCall(Call):
    """Reference to a file."""

    call_type: CallType = Field(default=CallType.FILE_CONTROL_ENTRY_CALL)


class IndexCall(Call):
    """Reference to an index."""

    call_type: CallType = Field(default=CallType.INDEX_CALL)


# =============================================================================
# ValueStmt Hierarchy
# =============================================================================


class ValueStmt(BaseModel):
    """
    Base class for value statements/expressions.

    Represents any expression or value in COBOL code.
    """

    value_stmt_type: ValueStmtType = Field(description="Type of value statement")
    sub_value_stmts: list[ValueStmt] = Field(default_factory=list, description="Nested expressions")
    location: SourceLocation | None = Field(default=None)

    model_config = {"extra": "allow"}


class LiteralValueStmt(ValueStmt):
    """Literal value."""

    value_stmt_type: ValueStmtType = Field(default=ValueStmtType.LITERAL)
    value: Any = Field(description="The literal value")
    literal_type: str = Field(default="STRING", description="Type: STRING, NUMERIC, FIGURATIVE")


class IntegerLiteralValueStmt(ValueStmt):
    """Integer literal."""

    value_stmt_type: ValueStmtType = Field(default=ValueStmtType.INTEGER_LITERAL)
    value: int = Field(description="Integer value")


class BooleanLiteralValueStmt(ValueStmt):
    """Boolean literal (TRUE/FALSE)."""

    value_stmt_type: ValueStmtType = Field(default=ValueStmtType.BOOLEAN_LITERAL)
    value: bool = Field(description="Boolean value")


class CallValueStmt(ValueStmt):
    """
    Reference to a data item as a value.

    Used when a variable is used in an expression.
    """

    value_stmt_type: ValueStmtType = Field(default=ValueStmtType.CALL_VALUE)
    call: Call = Field(description="The call/reference to the data item")


class ArithmeticValueStmt(ValueStmt):
    """Arithmetic expression."""

    value_stmt_type: ValueStmtType = Field(default=ValueStmtType.ARITHMETIC)
    operator: str | None = Field(default=None, description="Operator (+, -, *, /, **)")
    left_operand: ValueStmt | None = Field(default=None)
    right_operand: ValueStmt | None = Field(default=None)


class ConditionValueStmt(ValueStmt):
    """Conditional expression."""

    value_stmt_type: ValueStmtType = Field(default=ValueStmtType.CONDITION)
    condition_type: str | None = Field(default=None, description="AND, OR, NOT, etc.")


class RelationConditionValueStmt(ValueStmt):
    """Relational condition."""

    value_stmt_type: ValueStmtType = Field(default=ValueStmtType.RELATION_CONDITION)
    operator: str | None = Field(default=None, description="=, <, >, <=, >=, NOT =")
    left_operand: ValueStmt | None = Field(default=None)
    right_operand: ValueStmt | None = Field(default=None)


# =============================================================================
# Data Division Elements
# =============================================================================


class PictureClause(BaseModel):
    """COBOL PICTURE clause information."""

    picture_string: str = Field(description="The PICTURE string (e.g., '9(5)V99')")
    category: str | None = Field(
        default=None, description="Data category (NUMERIC, ALPHABETIC, etc.)"
    )
    size: int | None = Field(default=None, description="Size in bytes/characters")
    decimal_positions: int | None = Field(default=None, description="Number of decimal positions")
    is_signed: bool = Field(default=False, description="Whether the field is signed")
    is_numeric: bool = Field(default=False)
    is_alphabetic: bool = Field(default=False)
    is_alphanumeric: bool = Field(default=False)
    is_numeric_edited: bool = Field(default=False)
    is_alphanumeric_edited: bool = Field(default=False)


class ValueClause(BaseModel):
    """COBOL VALUE clause information."""

    value: Any = Field(description="The value (literal, figurative constant, etc.)")
    value_type: str = Field(default="LITERAL", description="Type of value")
    is_all: bool = Field(default=False, description="Whether ALL keyword is used")
    value_stmt: ValueStmt | None = Field(default=None, description="Parsed value expression")


class OccursSortKey(BaseModel):
    """OCCURS sort key specification."""

    key_call: Call | None = Field(default=None, description="Reference to the key field")
    key_name: str | None = Field(default=None, description="Key field name")
    is_ascending: bool = Field(default=True, description="True=ASCENDING, False=DESCENDING")


class OccursClause(BaseModel):
    """
    COBOL OCCURS clause information.

    Supports:
    - OCCURS n TIMES
    - OCCURS n TO m TIMES DEPENDING ON var
    - INDEXED BY index-name
    - KEY IS field-name ASCENDING/DESCENDING
    """

    # Basic count
    from_value: int | None = Field(
        default=None, description="OCCURS FROM value (for variable length)"
    )
    to_value: int | None = Field(default=None, description="OCCURS TO value (max occurrences)")

    # DEPENDING ON
    depending_on_call: Call | None = Field(
        default=None, description="Reference to DEPENDING ON variable"
    )
    depending_on_name: str | None = Field(
        default=None, description="DEPENDING ON variable name (convenience)"
    )

    # INDEXED BY
    index_calls: list[IndexCall] = Field(
        default_factory=list, description="INDEXED BY index references"
    )
    indexed_by: list[str] = Field(
        default_factory=list, description="INDEXED BY names (convenience)"
    )

    # KEY IS
    sort_keys: list[OccursSortKey] = Field(
        default_factory=list, description="Sort key specifications"
    )

    # Legacy compatibility
    min_occurs: int = Field(default=1, description="Minimum occurrences (from_value or 1)")
    max_occurs: int | None = Field(default=None, description="Maximum occurrences (to_value)")


class RedefinesClause(BaseModel):
    """COBOL REDEFINES clause information."""

    redefines_call: Call | None = Field(default=None, description="Reference to redefined entry")
    redefines_name: str = Field(description="Name of the redefined item")


class SynchronizedClause(BaseModel):
    """COBOL SYNCHRONIZED clause."""

    synchronized_type: SynchronizedType | None = Field(default=None, description="LEFT or RIGHT")


class SignClause(BaseModel):
    """COBOL SIGN clause."""

    sign_type: SignType = Field(description="Sign position type")
    is_separate: bool = Field(default=False, description="SEPARATE CHARACTER")


class ExternalClause(BaseModel):
    """COBOL EXTERNAL clause."""

    is_external: bool = Field(default=True)
    external_name: str | None = Field(default=None, description="External name if specified")


class GlobalClause(BaseModel):
    """COBOL GLOBAL clause."""

    is_global: bool = Field(default=True)


class JustifiedClause(BaseModel):
    """COBOL JUSTIFIED clause."""

    is_right: bool = Field(default=True, description="JUSTIFIED RIGHT")


class BlankWhenZeroClause(BaseModel):
    """COBOL BLANK WHEN ZERO clause."""

    is_blank_when_zero: bool = Field(default=True)


class AlignedClause(BaseModel):
    """COBOL ALIGNED clause."""

    aligned_type: AlignedType = Field(default=AlignedType.ALIGNED)


class CommonOwnLocalClause(BaseModel):
    """COBOL COMMON/OWN/LOCAL clause."""

    clause_type: CommonOwnLocalType = Field(description="COMMON, OWN, or LOCAL")


class ThreadLocalClause(BaseModel):
    """COBOL THREAD-LOCAL clause."""

    is_thread_local: bool = Field(default=True)


class TypeClause(BaseModel):
    """COBOL TYPE clause."""

    type_name: str = Field(description="Referenced type name")


class TypeDefClause(BaseModel):
    """COBOL TYPEDEF clause."""

    is_strong: bool = Field(default=False, description="STRONG TYPEDEF")


class UsingClause(BaseModel):
    """COBOL USING clause (data division context)."""

    using_type: str | None = Field(default=None)
    convention: str | None = Field(default=None)


class DataDescriptionEntry(ASGElement):
    """
    COBOL data description entry (variable definition).

    This model is intended to be comprehensive and JSON-friendly while supporting
    common COBOL clauses used for semantic analysis and cross-referencing.
    """

    level: int = Field(description="Level number (01-49, 66, 77, 88)")
    entry_type: DataDescriptionEntryType = Field(description="Entry type classification")

    # =========================================================================
    # Clause data (a superset of common COBOL data description clauses)
    # =========================================================================

    # Basic data definition clauses
    picture: PictureClause | None = Field(default=None, description="PICTURE clause")
    usage: UsageType | None = Field(default=None, description="USAGE clause type")
    value: ValueClause | None = Field(default=None, description="VALUE clause")
    occurs: OccursClause | None = Field(default=None, description="OCCURS clause")
    redefines: RedefinesClause | None = Field(default=None, description="REDEFINES clause")

    # Structural clauses
    synchronized: SynchronizedClause | None = Field(default=None, description="SYNCHRONIZED clause")
    sign_clause: SignClause | None = Field(default=None, description="SIGN clause")
    justified: JustifiedClause | None = Field(default=None, description="JUSTIFIED clause")
    blank_when_zero: BlankWhenZeroClause | None = Field(default=None, description="BLANK WHEN ZERO")

    # Scope clauses
    external: ExternalClause | None = Field(default=None, description="EXTERNAL clause")
    global_clause: GlobalClause | None = Field(default=None, description="GLOBAL clause")
    common_own_local: CommonOwnLocalClause | None = Field(
        default=None, description="COMMON/OWN/LOCAL"
    )
    thread_local: ThreadLocalClause | None = Field(default=None, description="THREAD-LOCAL clause")

    # Type clauses
    type_clause: TypeClause | None = Field(default=None, description="TYPE clause")
    type_def: TypeDefClause | None = Field(default=None, description="TYPEDEF clause")
    aligned: AlignedClause | None = Field(default=None, description="ALIGNED clause")

    # Advanced clauses
    using_clause: UsingClause | None = Field(default=None, description="USING clause")

    # Legacy boolean flags (for convenience/backward compatibility)
    is_filler: bool = Field(default=False, description="Whether this is a FILLER item")
    is_external: bool = Field(default=False, description="EXTERNAL clause present")
    is_global: bool = Field(default=False, description="GLOBAL clause present")
    is_justified_right: bool = Field(default=False, description="JUSTIFIED RIGHT")
    is_blank_when_zero: bool = Field(default=False, description="BLANK WHEN ZERO")
    sign_type: SignType | None = Field(default=None, description="SIGN clause (legacy)")

    # Filler tracking (sequential filler counter for disambiguation)
    filler_number: int | None = Field(default=None, description="Sequential filler counter")

    # =========================================================================
    # Hierarchical structure
    # =========================================================================

    children: list[DataDescriptionEntry] = Field(
        default_factory=list, description="Subordinate entries (for GROUP items)"
    )

    # Navigation (declaration order)
    predecessor_name: str | None = Field(
        default=None, description="Previous entry in declaration order"
    )
    successor_name: str | None = Field(default=None, description="Next entry in declaration order")
    parent_name: str | None = Field(default=None, description="Parent group item name")
    qualified_name: str | None = Field(
        default=None, description="Fully qualified name (e.g., 'CUST-ID OF CUSTOMER-RECORD')"
    )

    # Container info (where the entry is defined)
    container_type: str | None = Field(
        default=None, description="Container: FILE_SECTION, WORKING_STORAGE, LINKAGE_SECTION, etc."
    )

    # =========================================================================
    # Cross-references (incoming references: who uses this data item)
    # =========================================================================

    calls: list[DataDescriptionEntryCall] = Field(
        default_factory=list, description="All references TO this data item (who uses it)"
    )

    # =========================================================================
    # Condition-specific (level 88)
    # =========================================================================

    condition_values: list[Any] | None = Field(
        default=None, description="Values for level 88 conditions"
    )
    condition_through: Any | None = Field(default=None, description="THROUGH value for level 88")

    # =========================================================================
    # Rename-specific (level 66)
    # =========================================================================

    renames_from: str | None = Field(default=None, description="RENAMES starting item")
    renames_through: str | None = Field(default=None, description="RENAMES THROUGH ending item")


class FileDescriptionEntry(ASGElement):
    """
    COBOL file description entry (FD/SD).
    """

    file_type: str = Field(default="FD", description="FD or SD")
    record_name: str | None = Field(default=None, description="Record name")
    organization: FileOrganization | None = Field(default=None)
    access_mode: FileAccessMode | None = Field(default=None)
    record_key: str | None = Field(default=None, description="RECORD KEY")
    alternate_keys: list[str] = Field(default_factory=list)
    file_status: str | None = Field(default=None, description="FILE STATUS variable")
    block_contains: int | None = Field(default=None)
    record_contains_min: int | None = Field(default=None)
    record_contains_max: int | None = Field(default=None)
    label_records: str | None = Field(default=None, description="LABEL RECORDS clause")
    data_records: list[str] = Field(default_factory=list)

    # Record structure
    record_entries: list[DataDescriptionEntry] = Field(default_factory=list)


class FileControlEntry(ASGElement):
    """
    COBOL FILE-CONTROL entry (SELECT statement).

    Maps file names to physical files.
    """

    file_name: str = Field(description="Internal file name")
    assign_to: str | None = Field(default=None, description="External file assignment")
    organization: FileOrganization | None = Field(default=None)
    access_mode: FileAccessMode | None = Field(default=None)
    record_key: str | None = Field(default=None)
    alternate_keys: list[str] = Field(default_factory=list)
    file_status: str | None = Field(default=None)
    relative_key: str | None = Field(default=None)


# =============================================================================
# Data Division Sections
# =============================================================================


class WorkingStorageSection(ASGElement):
    """WORKING-STORAGE SECTION."""

    entries: list[DataDescriptionEntry] = Field(default_factory=list)


class LinkageSection(ASGElement):
    """LINKAGE SECTION - parameters passed to/from subprograms."""

    entries: list[DataDescriptionEntry] = Field(default_factory=list)


class LocalStorageSection(ASGElement):
    """LOCAL-STORAGE SECTION - thread-local storage."""

    entries: list[DataDescriptionEntry] = Field(default_factory=list)


class FileSection(ASGElement):
    """FILE SECTION - file and record definitions."""

    file_descriptions: list[FileDescriptionEntry] = Field(default_factory=list)


class CommunicationSection(ASGElement):
    """COMMUNICATION SECTION (legacy)."""

    entries: list[DataDescriptionEntry] = Field(default_factory=list)


class ReportSection(ASGElement):
    """REPORT SECTION."""

    entries: list[DataDescriptionEntry] = Field(default_factory=list)


class ScreenSection(ASGElement):
    """SCREEN SECTION."""

    entries: list[DataDescriptionEntry] = Field(default_factory=list)


class DataDivision(ASGElement):
    """
    COBOL DATA DIVISION.

    Contains all data definitions organized by section.
    """

    file_section: FileSection | None = Field(default=None)
    working_storage: WorkingStorageSection | None = Field(default=None)
    linkage_section: LinkageSection | None = Field(default=None)
    local_storage: LocalStorageSection | None = Field(default=None)
    communication_section: CommunicationSection | None = Field(default=None)
    report_section: ReportSection | None = Field(default=None)
    screen_section: ScreenSection | None = Field(default=None)

    # Symbol table for quick lookup
    symbol_table: dict[str, str] = Field(
        default_factory=dict, description="Map of variable names to qualified paths"
    )


# =============================================================================
# Procedure Division Elements
# =============================================================================


class CallParameter(BaseModel):
    """
    Parameter in a CALL statement.

    Supports BY REFERENCE, BY CONTENT, BY VALUE semantics, plus OMITTED.
    """

    name: str | None = Field(default=None, description="Variable name")
    value: Any | None = Field(default=None, description="Literal value if not a variable")
    parameter_type: ParameterType = Field(default=ParameterType.BY_REFERENCE)
    is_omitted: bool = Field(default=False, description="OMITTED keyword used")

    # Optional resolved reference to the data item
    call: DataDescriptionEntryCall | None = Field(
        default=None, description="Reference to parameter"
    )
    value_stmt: ValueStmt | None = Field(
        default=None, description="Value expression if not simple variable"
    )


class CallUsingPhrase(BaseModel):
    """CALL USING phrase."""

    parameters: list[CallParameter] = Field(default_factory=list)


class CallGivingPhrase(BaseModel):
    """CALL GIVING/RETURNING phrase."""

    giving_call: Call | None = Field(default=None, description="Reference to GIVING variable")
    giving_name: str | None = Field(default=None, description="GIVING variable name")


class CallStatement(ASGElement):
    """
    COBOL CALL statement.

    Critical for inter-program analysis and call graphs.
    """

    # Target program
    target_program: str = Field(description="Called program name")
    program_value_stmt: ValueStmt | None = Field(
        default=None, description="Program name as ValueStmt"
    )
    target_is_literal: bool = Field(
        default=True, description="True if target is literal, False if variable"
    )
    target_variable: str | None = Field(default=None, description="Variable name if dynamic call")

    # USING phrase (parameters)
    using_phrase: CallUsingPhrase | None = Field(
        default=None, description="USING phrase with parameters"
    )
    parameters: list[CallParameter] = Field(
        default_factory=list, description="USING parameters (convenience)"
    )

    # GIVING/RETURNING phrase
    giving_phrase: CallGivingPhrase | None = Field(
        default=None, description="GIVING/RETURNING phrase"
    )
    returning: str | None = Field(default=None, description="RETURNING variable (convenience)")

    # Exception handling
    on_exception: bool = Field(default=False, description="Has ON EXCEPTION clause")
    on_exception_statements: list[Statement] = Field(default_factory=list)
    not_on_exception: bool = Field(default=False, description="Has NOT ON EXCEPTION clause")
    not_on_exception_statements: list[Statement] = Field(default_factory=list)
    on_overflow: bool = Field(default=False, description="Has ON OVERFLOW clause")
    on_overflow_statements: list[Statement] = Field(default_factory=list)


class PerformVarying(BaseModel):
    """PERFORM VARYING clause."""

    varying_call: Call | None = Field(default=None, description="Reference to VARYING variable")
    varying_name: str | None = Field(default=None, description="VARYING variable name")

    from_value_stmt: ValueStmt | None = Field(default=None, description="FROM value")
    from_value: Any | None = Field(default=None, description="FROM value (convenience)")

    by_value_stmt: ValueStmt | None = Field(default=None, description="BY value")
    by_value: Any | None = Field(default=None, description="BY value (convenience)")

    until_condition: ConditionValueStmt | None = Field(default=None, description="UNTIL condition")
    until_text: str | None = Field(default=None, description="UNTIL condition as text")


class PerformTimes(BaseModel):
    """PERFORM TIMES clause."""

    times_value_stmt: ValueStmt | None = Field(default=None, description="TIMES value expression")
    times_value: int | None = Field(default=None, description="TIMES value (convenience)")


class PerformUntil(BaseModel):
    """PERFORM UNTIL clause."""

    condition: ConditionValueStmt | None = Field(default=None, description="UNTIL condition")
    condition_text: str | None = Field(default=None, description="UNTIL condition as text")
    is_test_before: bool = Field(default=True, description="WITH TEST BEFORE (default) vs AFTER")


class PerformInlineStatement(BaseModel):
    """Inline PERFORM."""

    perform_type: PerformType = Field(default=PerformType.SIMPLE)
    times: PerformTimes | None = Field(default=None)
    until: PerformUntil | None = Field(default=None)
    varying: PerformVarying | None = Field(default=None)
    statements: list[Statement] = Field(default_factory=list, description="Inline statement body")


class PerformProcedureStatement(BaseModel):
    """Procedure PERFORM (PERFORM para THRU para)."""

    # Procedure calls (resolved paragraph/section targets)
    procedure_calls: list[ProcedureCall] = Field(
        default_factory=list, description="Paragraph/section calls"
    )

    # Convenience fields
    target_paragraph: str | None = Field(default=None)
    through_paragraph: str | None = Field(default=None)

    perform_type: PerformType = Field(default=PerformType.SIMPLE)
    times: PerformTimes | None = Field(default=None)
    until: PerformUntil | None = Field(default=None)
    varying: PerformVarying | None = Field(default=None)


class PerformStatement(ASGElement):
    """
    COBOL PERFORM statement.

    Captures both:
    - Inline PERFORM (PERFORM ... END-PERFORM)
    - Procedure PERFORM (PERFORM para [THRU para])
    """

    # Structured representation
    perform_type: PerformType = Field(default=PerformType.SIMPLE)
    inline_statement: PerformInlineStatement | None = Field(default=None)
    procedure_statement: PerformProcedureStatement | None = Field(default=None)

    # Convenience fields (for backward compatibility)
    target_paragraph: str | None = Field(default=None, description="Target paragraph/section name")
    through_paragraph: str | None = Field(default=None, description="THRU paragraph name")
    is_inline: bool = Field(default=False, description="True if inline PERFORM")
    times: int | None = Field(default=None, description="TIMES value")
    until_condition: str | None = Field(default=None, description="UNTIL condition (as text)")
    varying_variable: str | None = Field(default=None, description="VARYING variable")
    varying_from: Any | None = Field(default=None)
    varying_by: Any | None = Field(default=None)
    varying_until: str | None = Field(default=None)


class MoveStatement(ASGElement):
    """COBOL MOVE statement."""

    source: str = Field(description="Source variable or literal")
    source_is_literal: bool = Field(default=False)
    source_value_stmt: ValueStmt | None = Field(default=None, description="Source as ValueStmt")

    targets: list[str] = Field(description="Target variable names")
    target_calls: list[DataDescriptionEntryCall] = Field(
        default_factory=list, description="Target references"
    )

    is_corresponding: bool = Field(default=False, description="MOVE CORRESPONDING")


class ComputeStatement(ASGElement):
    """COBOL COMPUTE statement."""

    targets: list[str] = Field(description="Target variables")
    target_calls: list[DataDescriptionEntryCall] = Field(
        default_factory=list, description="Target references"
    )

    expression: str = Field(description="Arithmetic expression (as text)")
    expression_value_stmt: ArithmeticValueStmt | None = Field(
        default=None, description="Parsed expression"
    )

    on_size_error: bool = Field(default=False)
    on_size_error_statements: list[Statement] = Field(default_factory=list)
    not_on_size_error: bool = Field(default=False)
    not_on_size_error_statements: list[Statement] = Field(default_factory=list)


class IfStatement(ASGElement):
    """COBOL IF statement."""

    condition: str = Field(description="Condition expression (as text)")
    condition_value_stmt: ConditionValueStmt | None = Field(
        default=None, description="Parsed condition"
    )

    then_statements: list[Statement] = Field(default_factory=list)
    else_statements: list[Statement] = Field(default_factory=list)
    is_nested_if: bool = Field(default=False)


class EvaluateWhen(BaseModel):
    """EVALUATE WHEN clause."""

    conditions: list[ValueStmt] = Field(default_factory=list, description="WHEN conditions")
    condition_texts: list[str] = Field(default_factory=list, description="Conditions as text")
    statements: list[Statement] = Field(default_factory=list)


class EvaluateStatement(ASGElement):
    """COBOL EVALUATE statement (case/switch)."""

    subjects: list[str] = Field(description="EVALUATE subjects")
    subject_value_stmts: list[ValueStmt] = Field(
        default_factory=list, description="Subjects as ValueStmt"
    )

    when_clauses: list[EvaluateWhen] = Field(default_factory=list, description="WHEN clauses")
    when_other_statements: list[Statement] = Field(default_factory=list)


class Statement(ASGElement):
    """
    Generic COBOL statement.

    For statements not requiring detailed semantic analysis,
    or as a container for statement type and basic info.
    """

    statement_type: StatementType = Field(description="Statement verb")

    # Common fields for reference resolution
    target: str | None = Field(
        default=None, description="Target for CALL, PERFORM, GO TO, file operations"
    )
    operands: list[str] = Field(
        default_factory=list, description="Data item operands for the statement"
    )

    # Specific statement details (populated based on type)
    call_details: CallStatement | None = Field(default=None)
    perform_details: PerformStatement | None = Field(default=None)
    move_details: MoveStatement | None = Field(default=None)
    compute_details: ComputeStatement | None = Field(default=None)
    if_details: IfStatement | None = Field(default=None)
    evaluate_details: EvaluateStatement | None = Field(default=None)

    # Raw text for statements without detailed parsing
    raw_text: str | None = Field(default=None, description="Original statement text")

    # References (resolved during semantic analysis)
    variables_read: list[str] = Field(
        default_factory=list, description="Variables read by this statement"
    )
    variables_written: list[str] = Field(
        default_factory=list, description="Variables modified by this statement"
    )
    procedures_called: list[str] = Field(
        default_factory=list, description="Paragraphs/sections performed"
    )


class Paragraph(ASGElement):
    """
    COBOL paragraph.

    A named block of statements within the PROCEDURE DIVISION.
    """

    # Explicit paragraph name field (useful when the BaseModel 'name' is used differently)
    paragraph_name: str | None = Field(default=None, description="Paragraph name")

    statements: list[Statement] = Field(default_factory=list)
    section_name: str | None = Field(default=None, description="Parent section name if any")

    # Analysis results
    statement_count: int = Field(default=0)
    statement_types: list[StatementType] = Field(default_factory=list)

    # Cross-references (incoming calls: who performs this paragraph)
    calls: list[ProcedureCall] = Field(
        default_factory=list, description="All PERFORM calls TO this paragraph (who calls me)"
    )

    # Legacy convenience fields
    called_by: list[str] = Field(
        default_factory=list, description="Paragraphs that PERFORM this one"
    )
    calls_to: list[str] = Field(default_factory=list, description="Paragraphs this one PERFORMs")
    called_by_count: int = Field(
        default=0, description="Number of unique callers (len of called_by)"
    )


class Section(ASGElement):
    """
    COBOL section.

    A named group of paragraphs within the PROCEDURE DIVISION.
    """

    paragraphs: list[Paragraph] = Field(default_factory=list)

    # Cross-references (incoming calls to this section)
    calls: list[SectionCall] = Field(
        default_factory=list, description="All PERFORM calls TO this section"
    )
    called_by: list[str] = Field(
        default_factory=list, description="Sections/paragraphs that PERFORM this section"
    )
    calls_to: list[str] = Field(
        default_factory=list, description="Sections/paragraphs this section PERFORMs"
    )
    called_by_count: int = Field(
        default=0, description="Number of unique callers (len of called_by)"
    )


class Declaratives(ASGElement):
    """
    COBOL DECLARATIVES section.

    Contains USE AFTER EXCEPTION/ERROR procedures.
    """

    sections: list[Section] = Field(default_factory=list, description="Declarative sections")


class ProcedureDivisionUsingClause(BaseModel):
    """PROCEDURE DIVISION USING clause."""

    parameters: list[Call] = Field(default_factory=list, description="Parameter references")
    parameter_names: list[str] = Field(
        default_factory=list, description="Parameter names (convenience)"
    )


class ProcedureDivisionGivingClause(BaseModel):
    """PROCEDURE DIVISION GIVING/RETURNING clause."""

    giving_call: Call | None = Field(default=None, description="GIVING/RETURNING reference")
    giving_name: str | None = Field(default=None, description="GIVING/RETURNING name")


class ProcedureDivision(ASGElement):
    """
    COBOL PROCEDURE DIVISION.

    Contains all executable code organized by sections and paragraphs.
    """

    # Sections
    sections: list[Section] = Field(default_factory=list)

    # Root paragraphs (not in sections)
    paragraphs: list[Paragraph] = Field(
        default_factory=list, description="Root paragraphs (not in sections)"
    )

    # USING clause (program parameters)
    using_clause: ProcedureDivisionUsingClause | None = Field(default=None)
    using_parameters: list[str] = Field(
        default_factory=list, description="USING parameter names (convenience)"
    )

    # GIVING clause
    giving_clause: ProcedureDivisionGivingClause | None = Field(default=None)
    returning_parameter: str | None = Field(
        default=None, description="RETURNING parameter name (convenience)"
    )

    # Declaratives
    declaratives: Declaratives | None = Field(default=None, description="DECLARATIVES section")
    has_declaratives: bool = Field(default=False)

    # Analysis results - for convenience
    call_statements: list[CallStatement] = Field(
        default_factory=list, description="All CALL statements for inter-program analysis"
    )

    # All paragraphs including those nested in sections
    all_paragraphs: list[Paragraph] = Field(
        default_factory=list, description="All paragraphs (including those in sections)"
    )


# =============================================================================
# Identification Division
# =============================================================================


class IdentificationDivision(ASGElement):
    """
    COBOL IDENTIFICATION DIVISION.

    Contains program identification and documentation.
    """

    program_id: str = Field(description="PROGRAM-ID")
    program_name: str | None = Field(default=None, description="Program name if different")
    is_initial: bool = Field(default=False, description="INITIAL clause")
    is_recursive: bool = Field(default=False, description="RECURSIVE clause")
    is_common: bool = Field(default=False, description="COMMON clause")

    # Optional documentation paragraphs
    author: str | None = Field(default=None)
    installation: str | None = Field(default=None)
    date_written: str | None = Field(default=None)
    date_compiled: str | None = Field(default=None)
    security: str | None = Field(default=None)
    remarks: str | None = Field(default=None)


# =============================================================================
# Environment Division
# =============================================================================


class SpecialNames(ASGElement):
    """SPECIAL-NAMES paragraph."""

    currency_sign: str | None = Field(default=None)
    decimal_point_is_comma: bool = Field(default=False)
    symbolic_characters: dict[str, int] = Field(default_factory=dict)
    class_definitions: dict[str, str] = Field(default_factory=dict)
    mnemonic_names: dict[str, str] = Field(default_factory=dict)


class ConfigurationSection(ASGElement):
    """CONFIGURATION SECTION."""

    source_computer: str | None = Field(default=None)
    object_computer: str | None = Field(default=None)
    special_names: SpecialNames | None = Field(default=None)
    repository: list[str] = Field(default_factory=list, description="REPOSITORY entries")


class InputOutputSection(ASGElement):
    """INPUT-OUTPUT SECTION."""

    file_control_entries: list[FileControlEntry] = Field(default_factory=list)


class EnvironmentDivision(ASGElement):
    """
    COBOL ENVIRONMENT DIVISION.

    Describes the computing environment.
    """

    configuration_section: ConfigurationSection | None = Field(default=None)
    input_output_section: InputOutputSection | None = Field(default=None)


# =============================================================================
# Program Unit and Compilation Unit
# =============================================================================


class ProgramUnit(ASGElement):
    """
    COBOL program unit.

    A complete COBOL program with all four divisions.
    """

    identification_division: IdentificationDivision = Field(description="IDENTIFICATION DIVISION")
    environment_division: EnvironmentDivision | None = Field(default=None)
    data_division: DataDivision | None = Field(default=None)
    procedure_division: ProcedureDivision | None = Field(default=None)

    # Nested programs (COBOL allows nested program definitions)
    nested_programs: list[ProgramUnit] = Field(default_factory=list)


class CompilationUnit(ASGElement):
    """
    COBOL compilation unit.

    Contains one or more program units from a single source file.
    """

    program_units: list[ProgramUnit] = Field(default_factory=list)

    # Copybook information
    copybooks_included: list[str] = Field(
        default_factory=list, description="Names of included copybooks"
    )

    # Preprocessing information
    preprocessed: bool = Field(default=False, description="Whether COPY statements were resolved")


# =============================================================================
# Top-Level Program (ASG Root)
# =============================================================================


class Program(BaseModel):
    """
    COBOL Program ASG root.

    Top-level container for the entire Abstract Semantic Graph.
    """

    # Metadata
    source_file: str = Field(description="Source file path")
    source_format: str = Field(
        default="FIXED", description="COBOL source format (FIXED, FREE, etc.)"
    )
    cobol_dialect: str | None = Field(default=None, description="COBOL dialect if known")
    parser_version: str = Field(default="1.0", description="Parser/ASG builder version")

    # Compilation units (usually one per file, but can be multiple)
    compilation_units: list[CompilationUnit] = Field(default_factory=list)

    # Cross-file analysis (for multi-program systems)
    external_calls: list[str] = Field(
        default_factory=list, description="Programs called via CALL statements"
    )
    external_copybooks: list[str] = Field(
        default_factory=list, description="External copybooks referenced"
    )

    # Copybook usage tracking
    copybook_usages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Copybooks used via COPY statements with resolution info",
    )

    # Analysis metadata
    analysis_timestamp: str | None = Field(default=None)
    errors: list[str] = Field(default_factory=list, description="Parsing/analysis errors")
    warnings: list[str] = Field(default_factory=list, description="Parsing/analysis warnings")

    model_config = {"extra": "allow"}


# =============================================================================
# Helper Functions
# =============================================================================


def create_data_entry(
    name: str,
    level: int,
    entry_type: DataDescriptionEntryType = DataDescriptionEntryType.ELEMENTARY,
    picture: str | None = None,
    value: Any = None,
    children: list[DataDescriptionEntry] | None = None,
) -> DataDescriptionEntry:
    """Helper to create a DataDescriptionEntry with common defaults."""
    entry = DataDescriptionEntry(
        name=name,
        level=level,
        entry_type=entry_type,
        children=children or [],
    )

    if picture:
        entry.picture = PictureClause(picture_string=picture)

    if value is not None:
        entry.value = ValueClause(value=value)

    return entry


def flatten_data_entries(entries: list[DataDescriptionEntry]) -> list[DataDescriptionEntry]:
    """Flatten nested data entries into a single list (preserves hierarchy info)."""
    result: list[DataDescriptionEntry] = []

    def _flatten(entry: DataDescriptionEntry, parent_name: str | None = None) -> None:
        entry_copy = entry.model_copy()
        entry_copy.parent_name = parent_name
        result.append(entry_copy)

        for child in entry.children:
            _flatten(child, entry.name)

    for entry in entries:
        _flatten(entry)

    return result


def build_symbol_table(data_division: DataDivision) -> dict[str, str]:
    """Build a simple symbol table mapping variable names to their qualified paths.

    For a more comprehensive symbol table with full metadata, use the SymbolTable class.
    """
    symbol_table: dict[str, str] = {}

    def _process_entries(entries: list[DataDescriptionEntry], prefix: str = "") -> None:
        for entry in entries:
            if entry.name and not entry.is_filler:
                qualified_name = f"{entry.name} OF {prefix}" if prefix else entry.name
                symbol_table[entry.name] = qualified_name

                if entry.children:
                    child_prefix = qualified_name if prefix else entry.name
                    _process_entries(entry.children, child_prefix)

    if data_division.working_storage:
        _process_entries(data_division.working_storage.entries)

    if data_division.linkage_section:
        _process_entries(data_division.linkage_section.entries)

    if data_division.file_section:
        for fd in data_division.file_section.file_descriptions:
            _process_entries(fd.record_entries, fd.name or "")

    return symbol_table


# =============================================================================
# Symbol Table Implementation
# =============================================================================


class SymbolType(str, Enum):
    """Types of symbols in the symbol table."""

    DATA_ITEM = "DATA_ITEM"  # Variable (level 01-49, 77)
    CONDITION_NAME = "CONDITION_NAME"  # Level 88
    RENAME = "RENAME"  # Level 66
    FILE = "FILE"  # FD/SD entry
    PARAGRAPH = "PARAGRAPH"  # Procedure paragraph
    SECTION = "SECTION"  # Procedure section
    PROGRAM = "PROGRAM"  # Program name
    INDEX = "INDEX"  # Index name from INDEXED BY
    MNEMONIC = "MNEMONIC"  # Mnemonic name from SPECIAL-NAMES


class SymbolScope(str, Enum):
    """Scope where a symbol is defined."""

    FILE_SECTION = "FILE_SECTION"
    WORKING_STORAGE = "WORKING_STORAGE"
    LOCAL_STORAGE = "LOCAL_STORAGE"
    LINKAGE_SECTION = "LINKAGE_SECTION"
    COMMUNICATION_SECTION = "COMMUNICATION_SECTION"
    REPORT_SECTION = "REPORT_SECTION"
    SCREEN_SECTION = "SCREEN_SECTION"
    PROCEDURE_DIVISION = "PROCEDURE_DIVISION"
    SPECIAL_NAMES = "SPECIAL_NAMES"
    GLOBAL = "GLOBAL"


class SymbolReference(BaseModel):
    """A reference to a symbol (where it's used)."""

    location: SourceLocation = Field(description="Where the reference occurs")
    context: str = Field(description="Statement type or context (MOVE, CALL, IF, etc.)")
    is_read: bool = Field(default=True, description="Symbol is read at this reference")
    is_write: bool = Field(default=False, description="Symbol is written at this reference")
    qualified_with: list[str] = Field(
        default_factory=list,
        description="Qualifiers used (e.g., ['CUSTOMER-RECORD'] for 'CUST-ID OF CUSTOMER-RECORD')",
    )


class SymbolEntry(BaseModel):
    """
    A symbol table entry with full metadata.

    Tracks everything known about a symbol: its definition,
    type information, and all references.
    """

    name: str = Field(description="Symbol name")
    symbol_type: SymbolType = Field(description="Type of symbol")
    scope: SymbolScope = Field(description="Scope where defined")

    # Definition location
    definition_location: SourceLocation | None = Field(default=None)

    # Qualified name for disambiguation
    qualified_name: str = Field(
        description="Fully qualified name (e.g., 'CUST-ID OF CUSTOMER-RECORD')"
    )
    qualification_path: list[str] = Field(
        default_factory=list, description="Path components ['CUSTOMER-RECORD', 'CUST-ID']"
    )

    # For data items
    level: int | None = Field(default=None, description="Level number for data items")
    data_type: DataDescriptionEntryType | None = Field(default=None)
    picture: str | None = Field(default=None, description="PICTURE string")
    usage: UsageType | None = Field(default=None)
    size_bytes: int | None = Field(default=None, description="Size in bytes")

    # Hierarchy
    parent_symbol: str | None = Field(default=None, description="Parent symbol qualified name")
    children_symbols: list[str] = Field(
        default_factory=list, description="Child symbol qualified names"
    )

    # For condition names (level 88)
    condition_values: list[Any] = Field(default_factory=list)

    # For paragraphs/sections
    performs_to: list[str] = Field(default_factory=list, description="Paragraphs this one PERFORMs")
    performed_by: list[str] = Field(
        default_factory=list, description="Paragraphs that PERFORM this one"
    )

    # Cross-references
    references: list[SymbolReference] = Field(
        default_factory=list, description="All references to this symbol"
    )

    # Flags
    is_external: bool = Field(default=False)
    is_global: bool = Field(default=False)
    is_redefined: bool = Field(default=False)
    redefines: str | None = Field(default=None, description="Symbol this one redefines")

    model_config = {"extra": "allow"}


class SymbolTable(BaseModel):
    """
    Comprehensive Symbol Table for COBOL ASG.

    Provides:
    - Symbol registration and lookup
    - Scope-based organization
    - Cross-reference tracking
    - Ambiguous name resolution
    - Hierarchical navigation

    Usage:
        st = SymbolTable()

        # Add symbols from data division
        st.add_data_symbol("CUST-ID", level=5, scope=SymbolScope.WORKING_STORAGE,
                          parent="CUSTOMER-RECORD", picture="9(10)")

        # Lookup
        symbol = st.lookup("CUST-ID")  # May return multiple if ambiguous
        symbol = st.lookup_qualified("CUST-ID OF CUSTOMER-RECORD")  # Exact match

        # Add reference
        st.add_reference("CUST-ID", location, context="MOVE", is_write=True)
    """

    # All symbols indexed by qualified name (unique)
    symbols: dict[str, SymbolEntry] = Field(default_factory=dict)

    # Index by simple name (may have multiple entries for same name)
    name_index: dict[str, list[str]] = Field(
        default_factory=dict, description="Maps simple names to list of qualified names"
    )

    # Index by scope
    scope_index: dict[SymbolScope, list[str]] = Field(
        default_factory=dict, description="Maps scopes to list of qualified names"
    )

    # Index by type
    type_index: dict[SymbolType, list[str]] = Field(
        default_factory=dict, description="Maps symbol types to list of qualified names"
    )

    # Program-level info
    program_name: str | None = Field(default=None)

    model_config = {"extra": "allow"}

    def add_symbol(self, entry: SymbolEntry) -> None:
        """Add a symbol to the table."""
        qualified_name = entry.qualified_name

        # Add to main index
        self.symbols[qualified_name] = entry

        # Add to name index
        if entry.name not in self.name_index:
            self.name_index[entry.name] = []
        if qualified_name not in self.name_index[entry.name]:
            self.name_index[entry.name].append(qualified_name)

        # Add to scope index
        if entry.scope not in self.scope_index:
            self.scope_index[entry.scope] = []
        if qualified_name not in self.scope_index[entry.scope]:
            self.scope_index[entry.scope].append(qualified_name)

        # Add to type index
        if entry.symbol_type not in self.type_index:
            self.type_index[entry.symbol_type] = []
        if qualified_name not in self.type_index[entry.symbol_type]:
            self.type_index[entry.symbol_type].append(qualified_name)

    def add_data_symbol(
        self,
        name: str,
        level: int,
        scope: SymbolScope,
        parent: str | None = None,
        picture: str | None = None,
        usage: UsageType | None = None,
        location: SourceLocation | None = None,
        is_filler: bool = False,
        **kwargs: Any,
    ) -> SymbolEntry:
        """Convenience method to add a data item symbol."""
        if is_filler:
            return SymbolEntry(
                name="FILLER",
                qualified_name=f"FILLER-{level}",
                symbol_type=SymbolType.DATA_ITEM,
                scope=scope,
                level=level,
            )

        # Build qualified name
        if parent:
            qualified_name = f"{name} OF {parent}"
            qualification_path = [*parent.split(" OF "), name]
        else:
            qualified_name = name
            qualification_path = [name]

        # Determine data type
        if level == 88:
            symbol_type = SymbolType.CONDITION_NAME
            data_type = DataDescriptionEntryType.CONDITION
        elif level == 66:
            symbol_type = SymbolType.RENAME
            data_type = DataDescriptionEntryType.RENAME
        else:
            symbol_type = SymbolType.DATA_ITEM
            data_type = (
                DataDescriptionEntryType.ELEMENTARY if picture else DataDescriptionEntryType.GROUP
            )

        entry = SymbolEntry(
            name=name,
            qualified_name=qualified_name,
            qualification_path=qualification_path,
            symbol_type=symbol_type,
            scope=scope,
            level=level,
            data_type=data_type,
            picture=picture,
            usage=usage,
            definition_location=location,
            parent_symbol=parent,
            **kwargs,
        )

        self.add_symbol(entry)

        # Update parent's children list
        if parent and parent in self.symbols:
            self.symbols[parent].children_symbols.append(qualified_name)

        return entry

    def add_paragraph_symbol(
        self,
        name: str,
        section: str | None = None,
        location: SourceLocation | None = None,
    ) -> SymbolEntry:
        """Add a paragraph symbol."""
        qualified_name = f"{name} IN {section}" if section else name

        entry = SymbolEntry(
            name=name,
            qualified_name=qualified_name,
            qualification_path=[section, name] if section else [name],
            symbol_type=SymbolType.PARAGRAPH,
            scope=SymbolScope.PROCEDURE_DIVISION,
            definition_location=location,
            parent_symbol=section,
        )

        self.add_symbol(entry)
        return entry

    def add_section_symbol(
        self,
        name: str,
        location: SourceLocation | None = None,
    ) -> SymbolEntry:
        """Add a section symbol."""
        entry = SymbolEntry(
            name=name,
            qualified_name=name,
            qualification_path=[name],
            symbol_type=SymbolType.SECTION,
            scope=SymbolScope.PROCEDURE_DIVISION,
            definition_location=location,
        )

        self.add_symbol(entry)
        return entry

    def add_reference(
        self,
        name: str,
        location: SourceLocation,
        context: str,
        is_read: bool = True,
        is_write: bool = False,
        qualifiers: list[str] | None = None,
    ) -> bool:
        """
        Add a reference to a symbol.

        Returns True if the symbol was found and reference added.
        """
        # Try to resolve the symbol
        resolved = self.resolve(name, qualifiers)
        if not resolved:
            return False

        ref = SymbolReference(
            location=location,
            context=context,
            is_read=is_read,
            is_write=is_write,
            qualified_with=qualifiers or [],
        )

        self.symbols[resolved].references.append(ref)
        return True

    def lookup(self, name: str) -> list[SymbolEntry]:
        """
        Lookup symbols by simple name.

        Returns all symbols with that name (may be multiple due to qualification).
        """
        if name not in self.name_index:
            return []

        return [self.symbols[qn] for qn in self.name_index[name] if qn in self.symbols]

    def lookup_qualified(self, qualified_name: str) -> SymbolEntry | None:
        """Lookup a symbol by its fully qualified name."""
        return self.symbols.get(qualified_name)

    def lookup_in_scope(self, name: str, scope: SymbolScope) -> list[SymbolEntry]:
        """Lookup symbols by name within a specific scope."""
        results = []
        for entry in self.lookup(name):
            if entry.scope == scope:
                results.append(entry)
        return results

    def resolve(self, name: str, qualifiers: list[str] | None = None) -> str | None:
        """
        Resolve a possibly-qualified name to a unique qualified name.

        Args:
            name: The symbol name to resolve
            qualifiers: Optional list of qualifiers (e.g., ['CUSTOMER-RECORD'] for
                       'CUST-ID OF CUSTOMER-RECORD')

        Returns:
            The qualified name if resolved uniquely, None if ambiguous or not found.
        """
        candidates = self.lookup(name)

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0].qualified_name

        # Multiple candidates - need qualifiers to disambiguate
        if not qualifiers:
            return None  # Ambiguous

        # Build expected qualified name pattern
        for entry in candidates:
            # Check if qualifiers match the qualification path
            matches = True
            for qualifier in qualifiers:
                if qualifier not in entry.qualification_path:
                    matches = False
                    break

            if matches:
                return entry.qualified_name

        return None  # No match found

    def get_by_scope(self, scope: SymbolScope) -> list[SymbolEntry]:
        """Get all symbols in a specific scope."""
        if scope not in self.scope_index:
            return []
        return [self.symbols[qn] for qn in self.scope_index[scope] if qn in self.symbols]

    def get_by_type(self, symbol_type: SymbolType) -> list[SymbolEntry]:
        """Get all symbols of a specific type."""
        if symbol_type not in self.type_index:
            return []
        return [self.symbols[qn] for qn in self.type_index[symbol_type] if qn in self.symbols]

    def get_data_items(self) -> list[SymbolEntry]:
        """Get all data item symbols."""
        return self.get_by_type(SymbolType.DATA_ITEM)

    def get_paragraphs(self) -> list[SymbolEntry]:
        """Get all paragraph symbols."""
        return self.get_by_type(SymbolType.PARAGRAPH)

    def get_sections(self) -> list[SymbolEntry]:
        """Get all section symbols."""
        return self.get_by_type(SymbolType.SECTION)

    def get_children(self, qualified_name: str) -> list[SymbolEntry]:
        """Get all child symbols of a given symbol."""
        if qualified_name not in self.symbols:
            return []

        entry = self.symbols[qualified_name]
        return [self.symbols[child] for child in entry.children_symbols if child in self.symbols]

    def get_parent(self, qualified_name: str) -> SymbolEntry | None:
        """Get the parent symbol of a given symbol."""
        if qualified_name not in self.symbols:
            return None

        entry = self.symbols[qualified_name]
        if entry.parent_symbol:
            return self.symbols.get(entry.parent_symbol)
        return None

    def get_unreferenced_symbols(self) -> list[SymbolEntry]:
        """Get all symbols that are never referenced (potential dead code)."""
        return [entry for entry in self.symbols.values() if not entry.references]

    def get_write_references(self, qualified_name: str) -> list[SymbolReference]:
        """Get all write references to a symbol."""
        if qualified_name not in self.symbols:
            return []
        return [ref for ref in self.symbols[qualified_name].references if ref.is_write]

    def get_read_references(self, qualified_name: str) -> list[SymbolReference]:
        """Get all read references to a symbol."""
        if qualified_name not in self.symbols:
            return []
        return [ref for ref in self.symbols[qualified_name].references if ref.is_read]

    def is_ambiguous(self, name: str) -> bool:
        """Check if a simple name is ambiguous (has multiple definitions)."""
        return name in self.name_index and len(self.name_index[name]) > 1

    def get_ambiguous_names(self) -> list[str]:
        """Get all names that have multiple definitions."""
        return [
            name for name, qualified_names in self.name_index.items() if len(qualified_names) > 1
        ]

    def to_dict(self) -> dict[str, Any]:
        """Export symbol table to dictionary for JSON serialization."""
        return {
            "program_name": self.program_name,
            "symbol_count": len(self.symbols),
            "symbols": {qn: entry.model_dump() for qn, entry in self.symbols.items()},
            "name_index": dict(self.name_index),
            "scope_summary": {scope.value: len(qns) for scope, qns in self.scope_index.items()},
            "type_summary": {stype.value: len(qns) for stype, qns in self.type_index.items()},
            "ambiguous_names": self.get_ambiguous_names(),
        }

    @classmethod
    def from_program_unit(cls, program_unit: ProgramUnit) -> SymbolTable:
        """Build a symbol table from a ProgramUnit."""
        st = cls()

        # Set program name
        if program_unit.identification_division:
            st.program_name = program_unit.identification_division.program_id

        # Process data division
        if program_unit.data_division:
            dd = program_unit.data_division

            # Working storage
            if dd.working_storage:
                cls._process_data_entries(
                    st, dd.working_storage.entries, SymbolScope.WORKING_STORAGE
                )

            # Linkage section
            if dd.linkage_section:
                cls._process_data_entries(
                    st, dd.linkage_section.entries, SymbolScope.LINKAGE_SECTION
                )

            # Local storage
            if dd.local_storage:
                cls._process_data_entries(st, dd.local_storage.entries, SymbolScope.LOCAL_STORAGE)

            # File section
            if dd.file_section:
                for fd in dd.file_section.file_descriptions:
                    # Add file symbol
                    st.add_symbol(
                        SymbolEntry(
                            name=fd.name or "UNKNOWN",
                            qualified_name=fd.name or "UNKNOWN",
                            qualification_path=[fd.name or "UNKNOWN"],
                            symbol_type=SymbolType.FILE,
                            scope=SymbolScope.FILE_SECTION,
                        )
                    )
                    # Add record entries
                    cls._process_data_entries(
                        st, fd.record_entries, SymbolScope.FILE_SECTION, parent=fd.name
                    )

        # Process procedure division
        if program_unit.procedure_division:
            pd = program_unit.procedure_division

            # Sections
            for section in pd.sections:
                st.add_section_symbol(section.name or "UNKNOWN")

                # Paragraphs in sections
                for para in section.paragraphs:
                    st.add_paragraph_symbol(para.name or "UNKNOWN", section=section.name)

            # Root paragraphs (not in sections)
            for para in pd.paragraphs:
                st.add_paragraph_symbol(para.name or "UNKNOWN")

        return st

    @classmethod
    def _process_data_entries(
        cls,
        st: SymbolTable,
        entries: list[DataDescriptionEntry],
        scope: SymbolScope,
        parent: str | None = None,
    ) -> None:
        """Recursively process data description entries."""
        for entry in entries:
            if entry.name:
                symbol = st.add_data_symbol(
                    name=entry.name,
                    level=entry.level,
                    scope=scope,
                    parent=parent,
                    picture=entry.picture.picture_string if entry.picture else None,
                    usage=entry.usage,
                    location=entry.location,
                    is_filler=entry.is_filler,
                    is_external=entry.is_external,
                    is_global=entry.is_global,
                )

                # Process children
                if entry.children:
                    cls._process_data_entries(
                        st, entry.children, scope, parent=symbol.qualified_name
                    )


# =============================================================================
# Reference Resolution System
# =============================================================================


class ReferenceType(str, Enum):
    """Types of references in COBOL code."""

    DATA_ITEM = "DATA_ITEM"  # Reference to a data item (variable)
    PARAGRAPH = "PARAGRAPH"  # PERFORM/GO TO paragraph
    SECTION = "SECTION"  # PERFORM/GO TO section
    PROGRAM = "PROGRAM"  # CALL target (inter-program)
    FILE = "FILE"  # File reference (OPEN, CLOSE, READ, WRITE)
    INDEX = "INDEX"  # Index reference (SET, SEARCH)
    CONDITION = "CONDITION"  # Level 88 condition name


class ResolutionStatus(str, Enum):
    """Status of reference resolution."""

    RESOLVED = "RESOLVED"  # Successfully resolved to a symbol
    AMBIGUOUS = "AMBIGUOUS"  # Multiple candidates, needs qualification
    NOT_FOUND = "NOT_FOUND"  # No matching symbol found
    EXTERNAL = "EXTERNAL"  # External reference (CALL to another program)


class ResolvedReference(BaseModel):
    """A resolved reference with full context."""

    # Reference information
    name: str = Field(description="The name as it appears in code")
    qualifiers: list[str] = Field(
        default_factory=list, description="Qualification chain (e.g., ['CUSTOMER-RECORD'])"
    )
    reference_type: ReferenceType = Field(description="Type of reference")

    # Resolution result
    status: ResolutionStatus = Field(description="Resolution status")
    resolved_symbol: str | None = Field(
        default=None, description="Qualified name of resolved symbol"
    )
    candidates: list[str] = Field(
        default_factory=list, description="Candidate symbols if ambiguous"
    )

    # Location information
    location: SourceLocation | None = Field(default=None, description="Where the reference occurs")
    context: str | None = Field(
        default=None, description="Statement context (e.g., 'MOVE', 'PERFORM')"
    )

    # Usage classification
    is_read: bool = Field(default=True, description="Is this a read access?")
    is_write: bool = Field(default=False, description="Is this a write access?")

    model_config = {"extra": "allow"}


class UnresolvedReference(BaseModel):
    """An unresolved reference for error reporting."""

    name: str = Field(description="The unresolved name")
    qualifiers: list[str] = Field(default_factory=list)
    reference_type: ReferenceType
    location: SourceLocation | None = None
    context: str | None = None
    reason: str = Field(description="Why resolution failed")
    suggestions: list[str] = Field(default_factory=list, description="Suggested similar symbols")

    model_config = {"extra": "allow"}


class ReferenceResolver(BaseModel):
    """
    Comprehensive reference resolver for COBOL ASG.

    Resolves references to data items, paragraphs, sections, and external programs.
    Handles COBOL-specific qualification rules for ambiguous names.

    Usage:
        resolver = ReferenceResolver(symbol_table=st)

        # Resolve a data item reference
        ref = resolver.resolve_data_reference("CUST-ID", qualifiers=["CUSTOMER-RECORD"])

        # Resolve a paragraph reference
        ref = resolver.resolve_paragraph_reference("VALIDATE-CUSTOMER")

        # Process all references in a statement
        refs = resolver.resolve_statement_references(statement)

        # Get resolution report
        report = resolver.get_resolution_report()
    """

    symbol_table: SymbolTable = Field(description="Symbol table to resolve against")

    # Resolution results
    resolved_references: list[ResolvedReference] = Field(default_factory=list)
    unresolved_references: list[UnresolvedReference] = Field(default_factory=list)

    # External program calls (for inter-program analysis)
    external_calls: dict[str, list[SourceLocation]] = Field(
        default_factory=dict, description="Map of called programs to call locations"
    )

    model_config = {"extra": "allow"}

    def resolve_data_reference(
        self,
        name: str,
        qualifiers: list[str] | None = None,
        location: SourceLocation | None = None,
        context: str | None = None,
        is_read: bool = True,
        is_write: bool = False,
    ) -> ResolvedReference:
        """
        Resolve a data item reference.

        COBOL allows ambiguous names that must be qualified:
            MOVE CUST-ID OF CUSTOMER-RECORD TO OUTPUT-ID

        Args:
            name: The data item name
            qualifiers: Optional list of qualifiers (parent names)
            location: Source location of the reference
            context: Statement context (MOVE, DISPLAY, etc.)
            is_read: Whether this is a read access
            is_write: Whether this is a write access

        Returns:
            ResolvedReference with resolution status
        """
        qualifiers = qualifiers or []

        # Look up candidates
        candidates = self.symbol_table.lookup(name)

        if not candidates:
            # Not found - create unresolved reference
            ref = ResolvedReference(
                name=name,
                qualifiers=qualifiers,
                reference_type=ReferenceType.DATA_ITEM,
                status=ResolutionStatus.NOT_FOUND,
                location=location,
                context=context,
                is_read=is_read,
                is_write=is_write,
            )
            self._add_unresolved(
                name, qualifiers, ReferenceType.DATA_ITEM, location, context, "Symbol not found"
            )
            self.resolved_references.append(ref)
            return ref

        if len(candidates) == 1:
            # Unique match
            symbol = candidates[0]
            ref = ResolvedReference(
                name=name,
                qualifiers=qualifiers,
                reference_type=ReferenceType.DATA_ITEM,
                status=ResolutionStatus.RESOLVED,
                resolved_symbol=symbol.qualified_name,
                location=location,
                context=context,
                is_read=is_read,
                is_write=is_write,
            )
            # Add to symbol's reference list
            if location:
                self.symbol_table.add_reference(
                    name, location, context or "", is_read, is_write, qualifiers
                )
            self.resolved_references.append(ref)
            return ref

        # Multiple candidates - try to resolve with qualifiers
        if qualifiers:
            resolved_name = self.symbol_table.resolve(name, qualifiers)
            if resolved_name:
                ref = ResolvedReference(
                    name=name,
                    qualifiers=qualifiers,
                    reference_type=ReferenceType.DATA_ITEM,
                    status=ResolutionStatus.RESOLVED,
                    resolved_symbol=resolved_name,
                    location=location,
                    context=context,
                    is_read=is_read,
                    is_write=is_write,
                )
                if location:
                    self.symbol_table.add_reference(
                        name, location, context or "", is_read, is_write, qualifiers
                    )
                self.resolved_references.append(ref)
                return ref

        # Ambiguous - cannot resolve
        ref = ResolvedReference(
            name=name,
            qualifiers=qualifiers,
            reference_type=ReferenceType.DATA_ITEM,
            status=ResolutionStatus.AMBIGUOUS,
            candidates=[c.qualified_name for c in candidates],
            location=location,
            context=context,
            is_read=is_read,
            is_write=is_write,
        )
        self._add_unresolved(
            name,
            qualifiers,
            ReferenceType.DATA_ITEM,
            location,
            context,
            f"Ambiguous: {len(candidates)} candidates",
            suggestions=[c.qualified_name for c in candidates],
        )
        self.resolved_references.append(ref)
        return ref

    def resolve_paragraph_reference(
        self,
        name: str,
        section: str | None = None,
        location: SourceLocation | None = None,
        context: str | None = None,
    ) -> ResolvedReference:
        """
        Resolve a paragraph reference (PERFORM, GO TO).

        Args:
            name: Paragraph name
            section: Optional section qualifier (for paragraphs in sections)
            location: Source location
            context: Statement context (PERFORM, GO TO)
        """
        qualifiers = [section] if section else []

        # Try qualified lookup first
        if section:
            qualified_name = f"{name} IN {section}"
            symbol = self.symbol_table.lookup_qualified(qualified_name)
            if symbol:
                ref = ResolvedReference(
                    name=name,
                    qualifiers=qualifiers,
                    reference_type=ReferenceType.PARAGRAPH,
                    status=ResolutionStatus.RESOLVED,
                    resolved_symbol=qualified_name,
                    location=location,
                    context=context,
                )
                self.resolved_references.append(ref)
                return ref

        # Try simple lookup
        candidates = self.symbol_table.lookup(name)
        paragraphs = [c for c in candidates if c.symbol_type == SymbolType.PARAGRAPH]

        if not paragraphs:
            # Check if it's a section
            sections = [c for c in candidates if c.symbol_type == SymbolType.SECTION]
            if sections:
                ref = ResolvedReference(
                    name=name,
                    qualifiers=qualifiers,
                    reference_type=ReferenceType.SECTION,
                    status=ResolutionStatus.RESOLVED,
                    resolved_symbol=sections[0].qualified_name,
                    location=location,
                    context=context,
                )
                self.resolved_references.append(ref)
                return ref

            # Not found
            ref = ResolvedReference(
                name=name,
                qualifiers=qualifiers,
                reference_type=ReferenceType.PARAGRAPH,
                status=ResolutionStatus.NOT_FOUND,
                location=location,
                context=context,
            )
            self._add_unresolved(
                name, qualifiers, ReferenceType.PARAGRAPH, location, context, "Paragraph not found"
            )
            self.resolved_references.append(ref)
            return ref

        if len(paragraphs) == 1:
            ref = ResolvedReference(
                name=name,
                qualifiers=qualifiers,
                reference_type=ReferenceType.PARAGRAPH,
                status=ResolutionStatus.RESOLVED,
                resolved_symbol=paragraphs[0].qualified_name,
                location=location,
                context=context,
            )
            self.resolved_references.append(ref)
            return ref

        # Ambiguous
        ref = ResolvedReference(
            name=name,
            qualifiers=qualifiers,
            reference_type=ReferenceType.PARAGRAPH,
            status=ResolutionStatus.AMBIGUOUS,
            candidates=[p.qualified_name for p in paragraphs],
            location=location,
            context=context,
        )
        self._add_unresolved(
            name,
            qualifiers,
            ReferenceType.PARAGRAPH,
            location,
            context,
            f"Ambiguous: {len(paragraphs)} paragraphs with same name",
            suggestions=[p.qualified_name for p in paragraphs],
        )
        self.resolved_references.append(ref)
        return ref

    def resolve_call_reference(
        self,
        target: str,
        location: SourceLocation | None = None,
        is_dynamic: bool = False,  # noqa: ARG002 - Reserved for future dynamic call handling
    ) -> ResolvedReference:
        """
        Resolve a CALL statement target.

        CALL targets are typically external programs, but could be entry points
        in the same compilation unit.

        Args:
            target: Called program name (may be literal or identifier)
            location: Source location of the CALL
            is_dynamic: Whether the CALL uses a variable (dynamic dispatch)
        """
        # Track external call
        if target not in self.external_calls:
            self.external_calls[target] = []
        if location:
            self.external_calls[target].append(location)

        # Check if it's an internal entry point
        internal_entries = self.symbol_table.lookup(target)
        entry_points = [e for e in internal_entries if e.symbol_type == SymbolType.PROGRAM]

        if entry_points:
            ref = ResolvedReference(
                name=target,
                qualifiers=[],
                reference_type=ReferenceType.PROGRAM,
                status=ResolutionStatus.RESOLVED,
                resolved_symbol=entry_points[0].qualified_name,
                location=location,
                context="CALL",
            )
        else:
            # External program
            ref = ResolvedReference(
                name=target,
                qualifiers=[],
                reference_type=ReferenceType.PROGRAM,
                status=ResolutionStatus.EXTERNAL,
                location=location,
                context="CALL",
            )

        self.resolved_references.append(ref)
        return ref

    def resolve_file_reference(
        self,
        name: str,
        location: SourceLocation | None = None,
        context: str | None = None,
    ) -> ResolvedReference:
        """Resolve a file reference (OPEN, CLOSE, READ, WRITE, etc.)."""
        candidates = self.symbol_table.lookup(name)
        files = [c for c in candidates if c.symbol_type == SymbolType.FILE]

        if not files:
            ref = ResolvedReference(
                name=name,
                qualifiers=[],
                reference_type=ReferenceType.FILE,
                status=ResolutionStatus.NOT_FOUND,
                location=location,
                context=context,
            )
            self._add_unresolved(name, [], ReferenceType.FILE, location, context, "File not found")
            self.resolved_references.append(ref)
            return ref

        ref = ResolvedReference(
            name=name,
            qualifiers=[],
            reference_type=ReferenceType.FILE,
            status=ResolutionStatus.RESOLVED,
            resolved_symbol=files[0].qualified_name,
            location=location,
            context=context,
        )
        self.resolved_references.append(ref)
        return ref

    def resolve_condition_reference(
        self,
        name: str,
        qualifiers: list[str] | None = None,
        location: SourceLocation | None = None,
        context: str | None = None,
    ) -> ResolvedReference:
        """Resolve a level 88 condition name reference."""
        qualifiers = qualifiers or []
        candidates = self.symbol_table.lookup(name)
        conditions = [c for c in candidates if c.symbol_type == SymbolType.CONDITION_NAME]

        if not conditions:
            ref = ResolvedReference(
                name=name,
                qualifiers=qualifiers,
                reference_type=ReferenceType.CONDITION,
                status=ResolutionStatus.NOT_FOUND,
                location=location,
                context=context,
            )
            self._add_unresolved(
                name, qualifiers, ReferenceType.CONDITION, location, context, "Condition not found"
            )
            self.resolved_references.append(ref)
            return ref

        if len(conditions) == 1:
            ref = ResolvedReference(
                name=name,
                qualifiers=qualifiers,
                reference_type=ReferenceType.CONDITION,
                status=ResolutionStatus.RESOLVED,
                resolved_symbol=conditions[0].qualified_name,
                location=location,
                context=context,
            )
            self.resolved_references.append(ref)
            return ref

        # Try qualifier resolution
        if qualifiers:
            for cond in conditions:
                matches = all(q in cond.qualification_path for q in qualifiers)
                if matches:
                    ref = ResolvedReference(
                        name=name,
                        qualifiers=qualifiers,
                        reference_type=ReferenceType.CONDITION,
                        status=ResolutionStatus.RESOLVED,
                        resolved_symbol=cond.qualified_name,
                        location=location,
                        context=context,
                    )
                    self.resolved_references.append(ref)
                    return ref

        # Ambiguous
        ref = ResolvedReference(
            name=name,
            qualifiers=qualifiers,
            reference_type=ReferenceType.CONDITION,
            status=ResolutionStatus.AMBIGUOUS,
            candidates=[c.qualified_name for c in conditions],
            location=location,
            context=context,
        )
        self._add_unresolved(
            name,
            qualifiers,
            ReferenceType.CONDITION,
            location,
            context,
            f"Ambiguous: {len(conditions)} conditions with same name",
            suggestions=[c.qualified_name for c in conditions],
        )
        self.resolved_references.append(ref)
        return ref

    def _resolve_move_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve MOVE statement references (source=read, target=write)."""
        refs: list[ResolvedReference] = []
        if statement.operands:
            for i, op in enumerate(statement.operands):
                is_write = i == len(statement.operands) - 1
                refs.append(
                    self.resolve_data_reference(
                        op,
                        location=statement.location,
                        context="MOVE",
                        is_read=not is_write,
                        is_write=is_write,
                    )
                )
        return refs

    def _resolve_paragraph_target_refs(
        self, statement: Statement, context: str
    ) -> list[ResolvedReference]:
        """Resolve PERFORM/GO TO target references."""
        if statement.target:
            return [
                self.resolve_paragraph_reference(
                    statement.target, location=statement.location, context=context
                )
            ]
        return []

    def _resolve_call_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve CALL statement references."""
        if statement.target:
            return [self.resolve_call_reference(statement.target, location=statement.location)]
        return []

    def _resolve_if_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve IF statement references (try condition first, then data item)."""
        refs: list[ResolvedReference] = []
        if statement.operands:
            for op in statement.operands:
                ref = self.resolve_condition_reference(
                    op, location=statement.location, context="IF"
                )
                if ref.status == ResolutionStatus.NOT_FOUND:
                    self.unresolved_references = [
                        u for u in self.unresolved_references if u.name != op or u.context != "IF"
                    ]
                    self.resolved_references = [r for r in self.resolved_references if r != ref]
                    ref = self.resolve_data_reference(
                        op, location=statement.location, context="IF", is_read=True
                    )
                refs.append(ref)
        return refs

    def _resolve_file_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve file operation references (OPEN, CLOSE, READ, WRITE, etc.)."""
        if statement.target:
            return [
                self.resolve_file_reference(
                    statement.target,
                    location=statement.location,
                    context=statement.statement_type.value,
                )
            ]
        return []

    def _resolve_arithmetic_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve arithmetic operation references (last operand is write target)."""
        refs: list[ResolvedReference] = []
        if statement.operands:
            for i, op in enumerate(statement.operands):
                is_last = i == len(statement.operands) - 1
                refs.append(
                    self.resolve_data_reference(
                        op,
                        location=statement.location,
                        context=statement.statement_type.value,
                        is_read=True,
                        is_write=is_last,
                    )
                )
        return refs

    def _resolve_display_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve DISPLAY statement references (read-only)."""
        return [
            self.resolve_data_reference(
                op, location=statement.location, context="DISPLAY", is_read=True
            )
            for op in (statement.operands or [])
        ]

    def _resolve_accept_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve ACCEPT statement references (write-only)."""
        return [
            self.resolve_data_reference(
                op, location=statement.location, context="ACCEPT", is_write=True, is_read=False
            )
            for op in (statement.operands or [])
        ]

    def _resolve_set_refs(self, statement: Statement) -> list[ResolvedReference]:
        """Resolve SET statement references (first operand is write target)."""
        refs: list[ResolvedReference] = []
        if statement.operands:
            for i, op in enumerate(statement.operands):
                is_target = i == 0
                refs.append(
                    self.resolve_data_reference(
                        op,
                        location=statement.location,
                        context="SET",
                        is_read=not is_target,
                        is_write=is_target,
                    )
                )
        return refs

    def resolve_statement_references(self, statement: Statement) -> list[ResolvedReference]:  # noqa: PLR0911
        """
        Resolve all references in a statement.

        Analyzes the statement type and resolves appropriate references.
        """
        stype = statement.statement_type

        # Data movement
        if stype == StatementType.MOVE:
            return self._resolve_move_refs(statement)

        # Control flow
        if stype == StatementType.PERFORM:
            return self._resolve_paragraph_target_refs(statement, "PERFORM")
        if stype == StatementType.GO_TO:
            return self._resolve_paragraph_target_refs(statement, "GO TO")
        if stype == StatementType.CALL:
            return self._resolve_call_refs(statement)

        # Conditional
        if stype == StatementType.IF:
            return self._resolve_if_refs(statement)

        # File operations
        if stype in (
            StatementType.OPEN,
            StatementType.CLOSE,
            StatementType.READ,
            StatementType.WRITE,
            StatementType.REWRITE,
            StatementType.DELETE,
        ):
            return self._resolve_file_refs(statement)

        # Arithmetic
        if stype in (
            StatementType.ADD,
            StatementType.SUBTRACT,
            StatementType.MULTIPLY,
            StatementType.DIVIDE,
            StatementType.COMPUTE,
        ):
            return self._resolve_arithmetic_refs(statement)

        # I/O
        if stype == StatementType.DISPLAY:
            return self._resolve_display_refs(statement)
        if stype == StatementType.ACCEPT:
            return self._resolve_accept_refs(statement)
        if stype == StatementType.SET:
            return self._resolve_set_refs(statement)

        return []

    def resolve_program_unit(self, program_unit: ProgramUnit) -> None:
        """
        Resolve all references in a program unit.

        Processes all statements in the procedure division.
        """
        if not program_unit.procedure_division:
            return

        pd = program_unit.procedure_division

        # Process sections
        for section in pd.sections:
            for paragraph in section.paragraphs:
                for statement in paragraph.statements:
                    self.resolve_statement_references(statement)

        # Process root paragraphs
        for paragraph in pd.paragraphs:
            for statement in paragraph.statements:
                self.resolve_statement_references(statement)

    def _add_unresolved(
        self,
        name: str,
        qualifiers: list[str],
        ref_type: ReferenceType,
        location: SourceLocation | None,
        context: str | None,
        reason: str,
        suggestions: list[str] | None = None,
    ) -> None:
        """Add an unresolved reference."""
        # Find similar names for suggestions
        if suggestions is None:
            suggestions = self._find_similar_names(name)

        self.unresolved_references.append(
            UnresolvedReference(
                name=name,
                qualifiers=qualifiers,
                reference_type=ref_type,
                location=location,
                context=context,
                reason=reason,
                suggestions=suggestions,
            )
        )

    def _find_similar_names(self, name: str, max_suggestions: int = 5) -> list[str]:
        """Find similar symbol names for suggestions."""
        suggestions = []
        name_upper = name.upper()

        for symbol_name in self.symbol_table.name_index:
            # Check for prefix or suffix match
            symbol_upper = symbol_name.upper()
            if symbol_name != name and (
                symbol_upper.startswith(name_upper[:3]) or name_upper[-3:] in symbol_upper
            ):
                suggestions.append(symbol_name)
                if len(suggestions) >= max_suggestions:
                    break

        return suggestions

    def get_resolution_report(self) -> dict[str, Any]:
        """Generate a resolution report."""
        resolved_count = sum(
            1 for r in self.resolved_references if r.status == ResolutionStatus.RESOLVED
        )
        ambiguous_count = sum(
            1 for r in self.resolved_references if r.status == ResolutionStatus.AMBIGUOUS
        )
        not_found_count = sum(
            1 for r in self.resolved_references if r.status == ResolutionStatus.NOT_FOUND
        )
        external_count = sum(
            1 for r in self.resolved_references if r.status == ResolutionStatus.EXTERNAL
        )

        return {
            "total_references": len(self.resolved_references),
            "resolved": resolved_count,
            "ambiguous": ambiguous_count,
            "not_found": not_found_count,
            "external": external_count,
            "resolution_rate": resolved_count / len(self.resolved_references)
            if self.resolved_references
            else 0,
            "external_calls": {prog: len(locs) for prog, locs in self.external_calls.items()},
            "unresolved_details": [u.model_dump() for u in self.unresolved_references],
            "by_type": {
                ref_type.value: sum(
                    1 for r in self.resolved_references if r.reference_type == ref_type
                )
                for ref_type in ReferenceType
            },
        }

    def get_call_graph_edges(self) -> list[tuple[str, str]]:
        """Get edges for inter-program call graph."""
        program_name = self.symbol_table.program_name or "UNKNOWN"
        return [(program_name, target) for target in self.external_calls]

    @classmethod
    def from_program_unit(
        cls, program_unit: ProgramUnit, symbol_table: SymbolTable | None = None
    ) -> ReferenceResolver:
        """
        Create a resolver and resolve all references in a program unit.

        Args:
            program_unit: The program unit to analyze
            symbol_table: Optional pre-built symbol table (will build one if not provided)

        Returns:
            ReferenceResolver with all references resolved
        """
        if symbol_table is None:
            symbol_table = SymbolTable.from_program_unit(program_unit)

        resolver = cls(symbol_table=symbol_table)
        resolver.resolve_program_unit(program_unit)
        return resolver
