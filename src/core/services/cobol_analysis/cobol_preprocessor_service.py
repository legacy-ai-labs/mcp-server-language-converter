"""
COBOL Preprocessor Service.

This service provides COBOL preprocessing capabilities:
- Line-by-line parsing with source format support (FIXED, TANDEM, VARIABLE)
- Indicator processing (comment *, /, debug D/d, continuation -, compiler $)
- Comment transformation to *> format for ANTLR compatibility
- Inline comment normalization
- Comment entries marking (AUTHOR., DATE-WRITTEN., etc.)
- COPY statement expansion with copybook resolution
- REPLACE directive processing
- REPLACING clause support in COPY statements
- Continuation line handling
- Source location tracking

Preprocessing pipeline:
1. CobolLineReader - Parse lines into structured CobolLine objects
2. CobolLineIndicatorProcessor - Process line indicators
3. CobolInlineCommentEntriesNormalizer - Normalize inline comments
4. CobolCommentEntriesMarker - Mark special comment entries
5. CobolDocumentParser - Process COPY/REPLACE/EXEC statements

Usage:
    from src.core.services.cobol_analysis.cobol_preprocessor_service import (
        CobolPreprocessor,
        PreprocessorConfig,
    )

    config = PreprocessorConfig(
        copybook_directories=[Path("copybooks")],
        source_format=SourceFormat.FIXED,
    )

    preprocessor = CobolPreprocessor(config)
    result = preprocessor.process_file(Path("program.cbl"))
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

CHAR_ASTERISK = "*"
CHAR_D = "D"
CHAR_D_LOWER = "d"
CHAR_DOLLAR_SIGN = "$"
CHAR_MINUS = "-"
CHAR_SLASH = "/"
CHAR_HASH = "#"
CHAR_TAB = "\t"
WS = " "

# Special tags for transformed content
COMMENT_TAG = "*>"
COMMENT_ENTRY_TAG = "*>CE"
EXEC_CICS_TAG = "*>EXECCICS"
EXEC_SQL_TAG = "*>EXECSQL"
EXEC_SQLIMS_TAG = "*>EXECSQLIMS"

NEWLINE = "\n"


# =============================================================================
# Source Format Definitions
# =============================================================================


class SourceFormat(str, Enum):
    """COBOL source format types with regex patterns."""

    FIXED = "FIXED"  # Standard ANSI/IBM: 1-6 seq, 7 indicator, 8-12 area A, 13-72 area B, 73-80 comments
    FREE = "FREE"  # Free format (no column restrictions) - alias for VARIABLE
    TANDEM = "TANDEM"  # HP Tandem: 1 indicator, 2-5 area A, 6-132 area B
    VARIABLE = "VARIABLE"  # Variable: 1-6 seq, 7 indicator, 8-12 area A, 13-* area B


# Indicator field pattern
INDICATOR_FIELD = r"([ABCdD$\t\-/*# ])"

# Regex patterns for each source format
SOURCE_FORMAT_PATTERNS = {
    SourceFormat.FIXED: re.compile(
        r"(.{0,6})(?:" + INDICATOR_FIELD + r"(.{0,4})(.{0,61})(.*))?", re.DOTALL
    ),
    SourceFormat.FREE: re.compile(
        r"(.{0,6})(?:" + INDICATOR_FIELD + r"(.{0,4})(.*)())?", re.DOTALL
    ),
    SourceFormat.TANDEM: re.compile(r"()(?:" + INDICATOR_FIELD + r"(.{0,4})(.*)())?", re.DOTALL),
    SourceFormat.VARIABLE: re.compile(
        r"(.{0,6})(?:" + INDICATOR_FIELD + r"(.{0,4})(.*)())?", re.DOTALL
    ),
}

# Whether the format supports multiline comment entries
FORMAT_COMMENT_ENTRY_MULTILINE = {
    SourceFormat.FIXED: True,
    SourceFormat.FREE: True,
    SourceFormat.TANDEM: False,
    SourceFormat.VARIABLE: True,
}


# =============================================================================
# Line Type Enumeration
# =============================================================================


class CobolLineType(str, Enum):
    """Types of COBOL source lines based on indicator field."""

    BLANK = "BLANK"
    COMMENT = "COMMENT"
    COMPILER_DIRECTIVE = "COMPILER_DIRECTIVE"
    CONTINUATION = "CONTINUATION"
    DEBUG = "DEBUG"
    NORMAL = "NORMAL"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class CobolLine:
    """
    Represents a parsed COBOL source line with all areas.

    Structure:
    - Sequence area (columns 1-6)
    - Indicator area (column 7)
    - Content area A (columns 8-12)
    - Content area B (columns 13-72)
    - Comment area (columns 73-80)
    """

    sequence_area: str
    indicator_area: str
    content_area_a: str
    content_area_b: str
    comment_area: str
    source_format: SourceFormat
    line_number: int
    line_type: CobolLineType

    # Original values (before transformation)
    sequence_area_original: str = ""
    indicator_area_original: str = ""
    content_area_a_original: str = ""
    content_area_b_original: str = ""
    comment_area_original: str = ""

    # Linked list navigation for continuation line handling
    predecessor: CobolLine | None = None
    successor: CobolLine | None = None

    def __post_init__(self) -> None:
        """Initialize original values if not set."""
        if not self.sequence_area_original:
            self.sequence_area_original = self.sequence_area
        if not self.indicator_area_original:
            self.indicator_area_original = self.indicator_area
        if not self.content_area_a_original:
            self.content_area_a_original = self.content_area_a
        if not self.content_area_b_original:
            self.content_area_b_original = self.content_area_b
        if not self.comment_area_original:
            self.comment_area_original = self.comment_area

    @property
    def content_area(self) -> str:
        """Get combined content area (A + B)."""
        return self.content_area_a + self.content_area_b

    @property
    def content_area_original(self) -> str:
        """Get original combined content area."""
        return self.content_area_a_original + self.content_area_b_original

    def serialize(self) -> str:
        """Serialize line back to string.

        The sequence area (cols 1-6) is blanked on output: ANTLR does not
        understand COBOL sequence numbers and treats them as code tokens.
        """
        blank_seq = WS * len(self.sequence_area) if self.sequence_area else ""
        return (
            blank_seq
            + self.indicator_area
            + self.content_area_a
            + self.content_area_b
            + self.comment_area
        )

    @classmethod
    def create_blank_sequence_area(cls, source_format: SourceFormat) -> str:
        """Create blank sequence area for format."""
        if source_format == SourceFormat.TANDEM:
            return ""
        return WS * 6

    def copy_with_indicator_and_content(self, indicator_area: str, content_area: str) -> CobolLine:
        """Create copy with new indicator and content areas."""
        content_a = content_area[:4] if len(content_area) > 4 else content_area
        content_b = content_area[4:] if len(content_area) > 4 else ""

        return CobolLine(
            sequence_area=self.sequence_area,
            indicator_area=indicator_area,
            content_area_a=content_a,
            content_area_b=content_b,
            comment_area=self.comment_area,
            source_format=self.source_format,
            line_number=self.line_number,
            line_type=self.line_type,
            sequence_area_original=self.sequence_area_original,
            indicator_area_original=self.indicator_area_original,
            content_area_a_original=self.content_area_a_original,
            content_area_b_original=self.content_area_b_original,
            comment_area_original=self.comment_area_original,
            predecessor=self.predecessor,
            successor=self.successor,
        )

    def copy_with_content(self, content_area: str) -> CobolLine:
        """Create copy with new content area."""
        content_a = content_area[:4] if len(content_area) > 4 else content_area
        content_b = content_area[4:] if len(content_area) > 4 else ""

        return CobolLine(
            sequence_area=self.sequence_area,
            indicator_area=self.indicator_area,
            content_area_a=content_a,
            content_area_b=content_b,
            comment_area=self.comment_area,
            source_format=self.source_format,
            line_number=self.line_number,
            line_type=self.line_type,
            sequence_area_original=self.sequence_area_original,
            indicator_area_original=self.indicator_area_original,
            content_area_a_original=self.content_area_a_original,
            content_area_b_original=self.content_area_b_original,
            comment_area_original=self.comment_area_original,
            predecessor=self.predecessor,
            successor=self.successor,
        )

    def copy_with_indicator(self, indicator_area: str) -> CobolLine:
        """Create copy with new indicator area."""
        return CobolLine(
            sequence_area=self.sequence_area,
            indicator_area=indicator_area,
            content_area_a=self.content_area_a,
            content_area_b=self.content_area_b,
            comment_area=self.comment_area,
            source_format=self.source_format,
            line_number=self.line_number,
            line_type=self.line_type,
            sequence_area_original=self.sequence_area_original,
            indicator_area_original=self.indicator_area_original,
            content_area_a_original=self.content_area_a_original,
            content_area_b_original=self.content_area_b_original,
            comment_area_original=self.comment_area_original,
            predecessor=self.predecessor,
            successor=self.successor,
        )


@dataclass
class PreprocessorConfig:
    """Configuration for the COBOL preprocessor."""

    # Copybook search directories (in order of priority)
    copybook_directories: list[Path] = field(default_factory=list)

    # File extensions to try when resolving copybooks
    copybook_extensions: list[str] = field(
        default_factory=lambda: [".cpy", ".CPY", ".copy", ".COPY", ".cbl", ".CBL", ""]
    )

    # Source format
    source_format: SourceFormat = SourceFormat.FIXED

    # Maximum depth for nested COPY statements (prevent infinite recursion)
    max_copy_depth: int = 10

    # Whether to preserve original line numbers in error messages
    preserve_line_mapping: bool = True

    # Whether to expand COPY statements (False = just track them)
    expand_copy_statements: bool = True

    # Whether to process REPLACE directives
    process_replace_directives: bool = True

    # Whether to remove/transform comment lines for ANTLR parsing
    remove_comment_lines: bool = True


@dataclass
class CopybookUsage:
    """Record of a COPY statement and its resolution."""

    copybook_name: str
    source_line: int
    source_column: int
    resolved_path: Path | None
    is_resolved: bool
    replacing_clauses: list[ReplacingClause] = field(default_factory=list)
    nested_in: str | None = None
    expansion_start_line: int | None = None
    expansion_end_line: int | None = None


@dataclass
class ReplacingClause:
    """A single REPLACING clause from a COPY statement."""

    old_text: str
    new_text: str
    is_pseudo_text: bool = False


@dataclass
class ReplaceDirective:
    """A REPLACE directive."""

    old_text: str
    new_text: str
    is_pseudo_text: bool = False
    source_line: int = 0
    is_active: bool = True


@dataclass
class LineMapping:
    """Maps preprocessed line number to original source."""

    preprocessed_line: int
    original_line: int
    original_file: str
    copybook_name: str | None = None


@dataclass
class PreprocessedSource:
    """Result of preprocessing a COBOL source file."""

    source: str
    original_source: str
    source_file: Path | None
    copybook_usages: list[CopybookUsage] = field(default_factory=list)
    replace_directives: list[ReplaceDirective] = field(default_factory=list)
    line_mappings: list[LineMapping] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if preprocessing had errors."""
        return len(self.errors) > 0

    @property
    def unresolved_copybooks(self) -> list[str]:
        """Get list of copybooks that could not be resolved."""
        return [u.copybook_name for u in self.copybook_usages if not u.is_resolved]

    def get_original_location(self, preprocessed_line: int) -> LineMapping | None:
        """Get original source location for a preprocessed line."""
        for mapping in self.line_mappings:
            if mapping.preprocessed_line == preprocessed_line:
                return mapping
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_file": str(self.source_file) if self.source_file else None,
            "preprocessed_line_count": len(self.source.splitlines()),
            "original_line_count": len(self.original_source.splitlines()),
            "copybook_usages": [
                {
                    "copybook_name": u.copybook_name,
                    "source_line": u.source_line,
                    "resolved_path": str(u.resolved_path) if u.resolved_path else None,
                    "is_resolved": u.is_resolved,
                    "replacing_clauses": [
                        {"old_text": r.old_text, "new_text": r.new_text}
                        for r in u.replacing_clauses
                    ],
                }
                for u in self.copybook_usages
            ],
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# Regex Patterns for Document Parsing
# =============================================================================

# COPY statement pattern
_COPY_PATTERN = re.compile(
    r"^\s*COPY\s+"
    r"(?P<copybook>[A-Za-z0-9_-]+|'[^']+\'|\"[^\"]+\")"
    r"(?:\s+(?:OF|IN)\s+(?P<library>[A-Za-z0-9_-]+|'[^']+\'|\"[^\"]+\"))?"
    r"(?P<replacing>\s+REPLACING\s+.*)?"
    r"\s*\.",
    re.IGNORECASE | re.MULTILINE,
)

# REPLACING clause pattern
_REPLACING_PATTERN = re.compile(
    r"(?:==(?P<old_pseudo>[^=]+)==|(?P<old_id>[A-Za-z0-9_-]+))"
    r"\s+BY\s+"
    r"(?:==(?P<new_pseudo>[^=]*)==|(?P<new_id>[A-Za-z0-9_-]*))",
    re.IGNORECASE,
)

# REPLACE directive pattern
_REPLACE_PATTERN = re.compile(
    r"^\s*REPLACE\s+"
    r"(?:(?P<off>OFF)|"
    r"(?:==(?P<old>[^=]+)==\s+BY\s+==(?P<new>[^=]*)==))"
    r"\s*\.",
    re.IGNORECASE | re.MULTILINE,
)

# Comment entry triggers (for AUTHOR., DATE-WRITTEN., etc.)
COMMENT_ENTRY_TRIGGERS_START = [
    "AUTHOR.",
    "INSTALLATION.",
    "DATE-WRITTEN.",
    "DATE-COMPILED.",
    "SECURITY.",
    "REMARKS.",
]

COMMENT_ENTRY_TRIGGERS_END = [
    "PROGRAM-ID.",
    "AUTHOR.",
    "INSTALLATION.",
    "DATE-WRITTEN.",
    "DATE-COMPILED.",
    "SECURITY.",
    "ENVIRONMENT",
    "DATA.",
    "PROCEDURE.",
]


# =============================================================================
# Line Reader (Stage 1)
# =============================================================================


class CobolLineReader:
    """
    Reads COBOL source and parses into CobolLine objects.

    Parses each line according to the source format (FIXED, TANDEM, VARIABLE)
    and extracts sequence area, indicator, content areas, and comments.
    """

    def determine_type(self, indicator_area: str) -> CobolLineType:
        """Determine line type from indicator area."""
        if indicator_area in (CHAR_D, CHAR_D_LOWER):
            return CobolLineType.DEBUG
        elif indicator_area == CHAR_MINUS:
            return CobolLineType.CONTINUATION
        elif indicator_area in (CHAR_ASTERISK, CHAR_SLASH):
            return CobolLineType.COMMENT
        elif indicator_area == CHAR_DOLLAR_SIGN:
            return CobolLineType.COMPILER_DIRECTIVE
        else:
            return CobolLineType.NORMAL

    def parse_line(self, line: str, line_number: int, source_format: SourceFormat) -> CobolLine:
        """Parse a single line into CobolLine structure."""
        pattern = SOURCE_FORMAT_PATTERNS[source_format]
        match = pattern.match(line)

        if not match:
            # Fallback for lines that don't match pattern
            logger.warning(
                f"Line {line_number + 1} doesn't match {source_format} format: {line[:40]}"
            )
            # Create a best-effort parse
            return CobolLine(
                sequence_area="",
                indicator_area=WS,
                content_area_a="",
                content_area_b=line.rstrip(),
                comment_area="",
                source_format=source_format,
                line_number=line_number,
                line_type=CobolLineType.NORMAL,
            )

        sequence_area = match.group(1) or ""
        indicator_area = match.group(2) or WS
        content_area_a = match.group(3) or ""
        content_area_b = match.group(4) or ""
        comment_area = match.group(5) or ""

        line_type = self.determine_type(indicator_area)

        return CobolLine(
            sequence_area=sequence_area,
            indicator_area=indicator_area,
            content_area_a=content_area_a,
            content_area_b=content_area_b,
            comment_area=comment_area,
            source_format=source_format,
            line_number=line_number,
            line_type=line_type,
        )

    def process_lines(self, source: str, source_format: SourceFormat) -> list[CobolLine]:
        """Process all lines from source."""
        result: list[CobolLine] = []
        last_line: CobolLine | None = None

        for line_number, line_text in enumerate(source.splitlines()):
            cobol_line = self.parse_line(line_text, line_number, source_format)

            # Link to predecessor
            if last_line:
                cobol_line.predecessor = last_line
                last_line.successor = cobol_line

            result.append(cobol_line)
            last_line = cobol_line

        return result


# =============================================================================
# Line Indicator Processor (Stage 2)
# =============================================================================


class CobolLineIndicatorProcessor:
    """
    Processes line indicators and transforms content.

    Responsibilities:
    - Removes sequence numbers
    - Transforms comment lines to *> format
    - Handles continuation lines
    - Processes debug lines
    """

    def is_next_line_continuation(self, line: CobolLine) -> bool:
        """Check if the next line is a continuation."""
        return line.successor is not None and line.successor.line_type == CobolLineType.CONTINUATION

    def is_ending_with_open_literal(self, line: CobolLine) -> bool:
        """Check if line ends with an open string literal."""
        content = line.content_area_original
        # Remove complete string literals and check for unmatched quotes
        content_without_literals = self._remove_string_literals(content)
        return '"' in content_without_literals or "'" in content_without_literals

    def _remove_string_literals(self, content: str) -> str:
        """Remove complete string literals from content."""
        # Remove double-quoted strings
        content = re.sub(r'"([^"]|""|\'\')*"', "", content)
        # Remove single-quoted strings
        content = re.sub(r"'([^']|''|\"\")*'", "", content)
        return content

    def conditional_right_trim_content_area(self, line: CobolLine) -> str:
        """Conditionally right-trim the content area."""
        if (not self.is_next_line_continuation(line)) or (
            not self.is_ending_with_open_literal(line)
        ):
            return self._right_trim_content_area(line.content_area)
        else:
            return line.content_area

    def _right_trim_content_area(self, content: str) -> str:
        """Right trim and repair trailing comma."""
        trimmed = content.rstrip()
        # Repair trimmed whitespace after comma separator
        if trimmed and trimmed[-1] in (",", ";"):
            trimmed += WS
        return trimmed

    def _trim_leading_whitespace(self, content: str) -> str:
        """Trim leading whitespace."""
        return content.lstrip()

    def _trim_leading_char(self, content: str) -> str:
        """Trim first character."""
        return content[1:] if content else ""

    def _process_continuation_line(self, line: CobolLine, content_area: str) -> CobolLine:
        """Process a continuation line.

        Handles continuation of string literals and default whitespace trimming.
        """
        if not content_area:
            return line.copy_with_indicator_and_content(WS, "")

        predecessor = line.predecessor

        # Handle continuation of string literals (explicit trailing quote on predecessor)
        if predecessor and (
            predecessor.content_area_original.endswith('"')
            or predecessor.content_area_original.endswith("'")
        ):
            trimmed = self._trim_leading_whitespace(content_area)
            if trimmed.startswith('"') or trimmed.startswith("'"):
                return line.copy_with_indicator_and_content(WS, self._trim_leading_char(trimmed))
            return line.copy_with_indicator_and_content(
                WS, self._trim_leading_whitespace(content_area)
            )

        # Handle open literal continuation (unmatched quote in predecessor)
        if predecessor and self.is_ending_with_open_literal(predecessor):
            trimmed = self._trim_leading_whitespace(content_area)
            if trimmed.startswith('"') or trimmed.startswith("'"):
                return line.copy_with_indicator_and_content(WS, self._trim_leading_char(trimmed))
            return line.copy_with_indicator_and_content(WS, content_area)

        # Closed literal continuation: prepend whitespace
        if predecessor and (
            predecessor.content_area.endswith('"') or predecessor.content_area.endswith("'")
        ):
            return line.copy_with_indicator_and_content(
                WS, WS + self._trim_leading_whitespace(content_area)
            )

        # Default: trim leading whitespace
        return line.copy_with_indicator_and_content(WS, self._trim_leading_whitespace(content_area))

    def process_line(self, line: CobolLine) -> CobolLine:
        """Process a single line based on its type."""
        content_area = self.conditional_right_trim_content_area(line)

        if line.line_type == CobolLineType.DEBUG:
            # Debug lines: replace indicator with space
            return line.copy_with_indicator_and_content(WS, content_area)

        elif line.line_type == CobolLineType.CONTINUATION:
            return self._process_continuation_line(line, content_area)

        elif line.line_type == CobolLineType.COMMENT:
            # Transform comment line: replace indicator with *> (comment tag + space)
            return line.copy_with_indicator_and_content(COMMENT_TAG + WS, content_area)

        elif line.line_type == CobolLineType.COMPILER_DIRECTIVE:
            # Compiler directive: empty the content
            return line.copy_with_indicator_and_content(WS, "")

        else:
            # Normal line: just replace indicator with space
            return line.copy_with_indicator_and_content(WS, content_area)

    def process_lines(self, lines: list[CobolLine]) -> list[CobolLine]:
        """Process all lines."""
        return [self.process_line(line) for line in lines]


# =============================================================================
# Inline Comment Normalizer (Stage 3)
# =============================================================================


class CobolInlineCommentEntriesNormalizer:
    """
    Normalizes inline comment entries.

    Ensures *> has a space after it (e.g., *>comment becomes *> comment).
    """

    # Pattern to find denormalized inline comments (no space after *>)
    _denormalized_pattern = re.compile(r"\*>[^ ]")

    def process_line(self, line: CobolLine) -> CobolLine:
        """Process a single line."""
        if not self._denormalized_pattern.search(line.content_area):
            return line

        # Add space after *> tags
        new_content = line.content_area.replace(COMMENT_TAG, COMMENT_TAG + WS)
        return line.copy_with_content(new_content)

    def process_lines(self, lines: list[CobolLine]) -> list[CobolLine]:
        """Process all lines."""
        return [self.process_line(line) for line in lines]


# =============================================================================
# Comment Entries Marker (Stage 4)
# =============================================================================


class CobolCommentEntriesMarker:
    """
    Marks special comment entries (AUTHOR., DATE-WRITTEN., etc.).

    These paragraphs contain free-form text that needs special handling
    to avoid ANTLR parsing errors.
    """

    def __init__(self) -> None:
        self._found_trigger_in_previous_line = False
        self._is_in_comment_entry = False

        # Pattern to match comment entry trigger lines
        trigger_pattern = r"([ \t]*)(" + "|".join(COMMENT_ENTRY_TRIGGERS_START) + r")(.+)"
        self._trigger_pattern = re.compile(trigger_pattern, re.IGNORECASE)

    def _starts_with_trigger(self, line: CobolLine, triggers: list[str]) -> bool:
        """Check if line starts with any trigger."""
        content_upper = line.content_area.upper().strip()
        return any(content_upper.startswith(trigger) for trigger in triggers)

    def _escape_comment_entry(self, line: CobolLine) -> CobolLine:
        """Escape comment entry by adding *>CE tag."""
        match = self._trigger_pattern.match(line.content_area)
        if not match:
            return line

        whitespace = match.group(1)
        trigger = match.group(2)
        comment_entry = match.group(3)
        new_content = f"{whitespace}{trigger}{WS}{COMMENT_ENTRY_TAG}{comment_entry}"
        return line.copy_with_content(new_content)

    def _build_multiline_comment_entry(self, line: CobolLine) -> CobolLine:
        """Mark line as part of multiline comment entry."""
        return line.copy_with_indicator(COMMENT_ENTRY_TAG + WS)

    def _is_in_comment_entry_check(self, line: CobolLine, is_content_area_a_empty: bool) -> bool:
        """Check if we're still in a comment entry."""
        return line.line_type == CobolLineType.COMMENT or is_content_area_a_empty

    def process_line_multiline(self, line: CobolLine) -> CobolLine:
        """Process line for multiline comment entry format (FIXED, VARIABLE)."""
        found_trigger_current = self._starts_with_trigger(line, COMMENT_ENTRY_TRIGGERS_START)

        if found_trigger_current:
            result = self._escape_comment_entry(line)
        elif self._found_trigger_in_previous_line or self._is_in_comment_entry:
            is_content_a_empty = line.content_area_a.strip() == ""
            self._is_in_comment_entry = self._is_in_comment_entry_check(line, is_content_a_empty)

            if self._is_in_comment_entry:
                result = self._build_multiline_comment_entry(line)
            else:
                result = line
        else:
            result = line

        self._found_trigger_in_previous_line = found_trigger_current
        return result

    def process_line_singleline(self, line: CobolLine) -> CobolLine:
        """Process line for single-line comment entry format (TANDEM)."""
        if self._starts_with_trigger(line, COMMENT_ENTRY_TRIGGERS_START):
            return self._escape_comment_entry(line)
        return line

    def process_line(self, line: CobolLine) -> CobolLine:
        """Process a single line."""
        if FORMAT_COMMENT_ENTRY_MULTILINE[line.source_format]:
            return self.process_line_multiline(line)
        else:
            return self.process_line_singleline(line)

    def process_lines(self, lines: list[CobolLine]) -> list[CobolLine]:
        """Process all lines."""
        # Reset state
        self._found_trigger_in_previous_line = False
        self._is_in_comment_entry = False

        return [self.process_line(line) for line in lines]


# =============================================================================
# Line Writer
# =============================================================================


class CobolLineWriter:
    """Serializes CobolLine objects back to string."""

    def serialize(self, lines: list[CobolLine]) -> str:
        """Serialize lines to string."""
        return NEWLINE.join(line.serialize() for line in lines)


# =============================================================================
# Main Preprocessor
# =============================================================================


class CobolPreprocessorError(Exception):
    """Exception raised during COBOL preprocessing."""

    pass


class CobolPreprocessor:
    """
    COBOL Preprocessor for preparing source code for ANTLR parsing.

    Preprocessing pipeline:
    1. Line reading and parsing
    2. Line indicator processing
    3. Inline comment normalization
    4. Comment entries marking
    5. Document parsing (COPY/REPLACE)
    """

    def __init__(self, config: PreprocessorConfig | None = None):
        """Initialize preprocessor with configuration."""
        self.config = config or PreprocessorConfig()
        self._copybook_cache: dict[str, str] = {}
        self._active_replaces: list[ReplaceDirective] = []

        # Initialize pipeline components
        self._line_reader = CobolLineReader()
        self._indicator_processor = CobolLineIndicatorProcessor()
        self._inline_normalizer = CobolInlineCommentEntriesNormalizer()
        self._comment_marker = CobolCommentEntriesMarker()
        self._line_writer = CobolLineWriter()

    def process_file(self, file_path: Path) -> PreprocessedSource:
        """Preprocess a COBOL source file."""
        if not file_path.exists():
            raise FileNotFoundError(f"COBOL source file not found: {file_path}")

        source = file_path.read_text(encoding="utf-8", errors="replace")
        search_dirs = [file_path.parent, *self.config.copybook_directories]

        return self._process_source(source, file_path, search_dirs)

    def process_source(
        self,
        source: str,
        source_file: Path | None = None,
        copybook_directories: list[Path] | None = None,
    ) -> PreprocessedSource:
        """Preprocess COBOL source code string."""
        search_dirs = list(self.config.copybook_directories)
        if copybook_directories:
            search_dirs = [*copybook_directories, *search_dirs]
        if source_file:
            search_dirs = [source_file.parent, *search_dirs]

        return self._process_source(source, source_file, search_dirs)

    def _process_source(
        self,
        source: str,
        source_file: Path | None,
        search_dirs: list[Path],
        depth: int = 0,
        parent_copybook: str | None = None,
    ) -> PreprocessedSource:
        """Internal method to process source."""
        result = PreprocessedSource(
            source=source,
            original_source=source,
            source_file=source_file,
        )

        # Check recursion depth
        if depth > self.config.max_copy_depth:
            result.errors.append(
                f"Maximum COPY nesting depth ({self.config.max_copy_depth}) exceeded"
            )
            return result

        # Reset state for top-level
        if depth == 0:
            self._active_replaces = []

        # Stage 1: Read lines
        lines = self._line_reader.process_lines(source, self.config.source_format)

        # Stage 2: Process line indicators
        lines = self._indicator_processor.process_lines(lines)

        # Stage 3: Normalize inline comments
        lines = self._inline_normalizer.process_lines(lines)

        # Stage 4: Mark comment entries
        lines = self._comment_marker.process_lines(lines)

        # Stage 5: Serialize back to string
        processed_source = self._line_writer.serialize(lines)

        # Stage 6: Process REPLACE directives
        if self.config.process_replace_directives:
            processed_source = self._process_replace_directives(processed_source, result)

        # Stage 7: Process COPY statements
        if self.config.expand_copy_statements:
            processed_source = self._process_copy_statements(
                processed_source, result, search_dirs, depth, parent_copybook
            )

        # Stage 8: Apply active REPLACE directives
        if self._active_replaces:
            processed_source = self._apply_replace_directives(processed_source)

        result.source = processed_source
        return result

    def _process_replace_directives(self, source: str, result: PreprocessedSource) -> str:
        """Process REPLACE directives."""
        lines = source.splitlines()
        processed_lines: list[str] = []

        for i, line in enumerate(lines):
            match = _REPLACE_PATTERN.search(line)
            if match:
                if match.group("off"):
                    for directive in self._active_replaces:
                        directive.is_active = False
                    result.replace_directives.append(
                        ReplaceDirective(
                            old_text="",
                            new_text="",
                            source_line=i + 1,
                            is_active=False,
                        )
                    )
                else:
                    old_text = match.group("old") or ""
                    new_text = match.group("new") or ""
                    directive = ReplaceDirective(
                        old_text=old_text.strip(),
                        new_text=new_text.strip(),
                        is_pseudo_text=True,
                        source_line=i + 1,
                        is_active=True,
                    )
                    self._active_replaces.append(directive)
                    result.replace_directives.append(directive)
                # Replace line with blank
                processed_lines.append("")
            else:
                processed_lines.append(line)

        return NEWLINE.join(processed_lines)

    def _process_copy_statements(
        self,
        source: str,
        result: PreprocessedSource,
        search_dirs: list[Path],
        depth: int,
        parent_copybook: str | None,
    ) -> str:
        """Process COPY statements and expand copybooks."""
        lines = source.splitlines()
        processed_lines: list[str] = []
        i = 0

        copy_buffer = ""
        copy_start_line = 0

        while i < len(lines):
            line = lines[i]

            # Handle continuation of COPY statement
            if copy_buffer:
                copy_buffer += " " + line.strip()

                if "." in copy_buffer:
                    expanded = self._expand_copy_statement(
                        copy_buffer, copy_start_line, result, search_dirs, depth, parent_copybook
                    )
                    processed_lines.extend(expanded.splitlines())
                    copy_buffer = ""
                i += 1
                continue

            # Check for COPY statement
            line_upper = line.strip().upper()
            if line_upper.startswith("COPY "):
                copy_buffer = line.strip()
                copy_start_line = i + 1

                if "." in copy_buffer:
                    expanded = self._expand_copy_statement(
                        copy_buffer, copy_start_line, result, search_dirs, depth, parent_copybook
                    )
                    processed_lines.extend(expanded.splitlines())
                    copy_buffer = ""
            else:
                processed_lines.append(line)

            i += 1

        return NEWLINE.join(processed_lines)

    def _expand_copy_statement(
        self,
        copy_text: str,
        source_line: int,
        result: PreprocessedSource,
        search_dirs: list[Path],
        depth: int,
        parent_copybook: str | None,
    ) -> str:
        """Expand a single COPY statement."""
        match = _COPY_PATTERN.match(copy_text)
        if not match:
            result.warnings.append(
                f"Line {source_line}: Could not parse COPY statement: {copy_text[:50]}"
            )
            return ""

        copybook_name = match.group("copybook").strip("'\"")
        library_name = match.group("library")
        if library_name:
            library_name = library_name.strip("'\"")

        # Parse REPLACING clause
        replacing_clauses: list[ReplacingClause] = []
        replacing_text = match.group("replacing")
        if replacing_text:
            replacing_clauses = self._parse_replacing_clause(replacing_text)

        # Resolve copybook
        resolved_path = self._resolve_copybook(copybook_name, library_name, search_dirs)

        # Record usage
        usage = CopybookUsage(
            copybook_name=copybook_name,
            source_line=source_line,
            source_column=7,
            resolved_path=resolved_path,
            is_resolved=resolved_path is not None,
            replacing_clauses=replacing_clauses,
            nested_in=parent_copybook,
        )
        result.copybook_usages.append(usage)

        if not resolved_path:
            result.errors.append(f"Line {source_line}: Copybook not found: {copybook_name}")
            return ""

        # Read copybook
        try:
            copybook_content = self._read_copybook(resolved_path)
        except Exception as e:
            result.errors.append(f"Line {source_line}: Error reading copybook {copybook_name}: {e}")
            return ""

        # Apply REPLACING clause
        if replacing_clauses:
            copybook_content = self._apply_replacing(copybook_content, replacing_clauses)

        # Recursively process
        nested_result = self._process_source(
            copybook_content, resolved_path, search_dirs, depth + 1, copybook_name
        )

        result.copybook_usages.extend(nested_result.copybook_usages)
        result.errors.extend(nested_result.errors)
        result.warnings.extend(nested_result.warnings)

        return nested_result.source

    def _resolve_copybook(
        self, copybook_name: str, library_name: str | None, search_dirs: list[Path]
    ) -> Path | None:
        """Resolve copybook name to file path."""
        dirs_to_search = list(search_dirs)

        if library_name:
            for base_dir in search_dirs:
                lib_dir = base_dir / library_name
                if lib_dir.exists():
                    dirs_to_search.insert(0, lib_dir)

        for search_dir in dirs_to_search:
            if not search_dir.exists():
                continue

            for ext in self.config.copybook_extensions:
                for name in [copybook_name, copybook_name.upper(), copybook_name.lower()]:
                    candidate = search_dir / f"{name}{ext}"
                    if candidate.exists():
                        return candidate

        return None

    def _read_copybook(self, path: Path) -> str:
        """Read copybook content with caching."""
        cache_key = str(path.resolve())
        if cache_key in self._copybook_cache:
            return self._copybook_cache[cache_key]

        content = path.read_text(encoding="utf-8", errors="replace")
        self._copybook_cache[cache_key] = content
        return content

    def _parse_replacing_clause(self, replacing_text: str) -> list[ReplacingClause]:
        """Parse REPLACING clause."""
        clauses: list[ReplacingClause] = []

        for match in _REPLACING_PATTERN.finditer(replacing_text):
            old_pseudo = match.group("old_pseudo")
            new_pseudo = match.group("new_pseudo")
            old_id = match.group("old_id")
            new_id = match.group("new_id")

            if old_pseudo is not None:
                clauses.append(
                    ReplacingClause(
                        old_text=old_pseudo.strip(),
                        new_text=(new_pseudo or "").strip(),
                        is_pseudo_text=True,
                    )
                )
            elif old_id:
                clauses.append(
                    ReplacingClause(
                        old_text=old_id,
                        new_text=new_id or "",
                        is_pseudo_text=False,
                    )
                )

        return clauses

    def _apply_replacing(self, content: str, clauses: list[ReplacingClause]) -> str:
        """Apply REPLACING clauses to content."""
        result = content

        for clause in clauses:
            if clause.is_pseudo_text:
                old_pattern = re.escape(clause.old_text)
                old_pattern = r"\s+".join(old_pattern.split(r"\ "))
                result = re.sub(old_pattern, clause.new_text, result, flags=re.IGNORECASE)
            else:
                old_pattern = r"\b" + re.escape(clause.old_text) + r"\b"
                result = re.sub(old_pattern, clause.new_text, result, flags=re.IGNORECASE)

        return result

    def _apply_replace_directives(self, source: str) -> str:
        """Apply active REPLACE directives."""
        result = source

        for directive in self._active_replaces:
            if not directive.is_active:
                continue
            if directive.is_pseudo_text:
                old_pattern = re.escape(directive.old_text)
                old_pattern = r"\s+".join(old_pattern.split(r"\ "))
                result = re.sub(old_pattern, directive.new_text, result, flags=re.IGNORECASE)

        return result

    def clear_cache(self) -> None:
        """Clear the copybook cache."""
        self._copybook_cache.clear()


# =============================================================================
# Convenience Functions
# =============================================================================


def preprocess_cobol_file(
    file_path: Path,
    copybook_directories: list[Path] | None = None,
    source_format: SourceFormat = SourceFormat.FIXED,
) -> PreprocessedSource:
    """Convenience function to preprocess a COBOL file."""
    config = PreprocessorConfig(
        copybook_directories=copybook_directories or [],
        source_format=source_format,
    )
    preprocessor = CobolPreprocessor(config)
    return preprocessor.process_file(file_path)


def preprocess_cobol_source(
    source: str,
    copybook_directories: list[Path] | None = None,
    source_format: SourceFormat = SourceFormat.FIXED,
) -> PreprocessedSource:
    """Convenience function to preprocess COBOL source code."""
    config = PreprocessorConfig(
        copybook_directories=copybook_directories or [],
        source_format=source_format,
    )
    preprocessor = CobolPreprocessor(config)
    return preprocessor.process_source(source)
