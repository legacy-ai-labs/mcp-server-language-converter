# Step 1: COBOL Parser Research & Selection

## Research Date
2024

## Objective
Identify and select a COBOL parser library suitable for building AST, CFG, and DFG from COBOL source code.

## Requirements

### Functional Requirements
- Parse COBOL source code (fixed-format and free-format)
- Support all four COBOL divisions (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)
- Handle common COBOL constructs:
  - Paragraphs and sections
  - PERFORM statements
  - GOTO statements
  - CALL statements
  - IF/ELSE conditionals
  - EVALUATE statements
  - File definitions (FD, SELECT)
  - WORKING-STORAGE and LINKAGE sections
- Produce parse tree suitable for AST construction
- Preserve source location information (line numbers, columns)

### Technical Requirements
- Python-compatible
- Can be integrated into existing project
- Active maintenance or stable codebase
- Good documentation
- License compatible with project

## Research Findings

### Option 1: Cobol-REKT

**Source**: https://github.com/avishek-sen-gupta/cobol-rekt

**Description**: Toolkit for reverse engineering legacy COBOL code with capabilities for:
- Flowchart generation
- Parse tree creation
- Control flow analysis
- Support for various COBOL dialects (standard COBOL, IDMS, CICS, DB2)

**Pros**:
- Specifically designed for reverse engineering
- Includes CFG generation capabilities
- Supports multiple COBOL dialects
- Open source

**Cons**:
- Need to verify Python compatibility
- May be more than needed (includes visualization)
- Need to assess code quality and maintenance status

**Status**: Requires further investigation

---

### Option 2: ANTLR with COBOL Grammar

**Description**: Use ANTLR (parser generator) with existing COBOL grammar files.

**Approach**:
1. Find or create ANTLR COBOL grammar file (.g4)
2. Generate Python parser using ANTLR4
3. Integrate generated parser into project

**Pros**:
- ANTLR is mature and well-documented
- Grammar-based approach (declarative)
- Can customize grammar for specific needs
- Good Python support (antlr4-python3-runtime)
- Many existing grammars available

**Cons**:
- Requires grammar file (may need to create/modify)
- Generated code can be verbose
- Learning curve for ANTLR
- May need to handle grammar conflicts

**Resources**:
- ANTLR4 Python runtime: `antlr4-python3-runtime`
- COBOL grammar files may be available on GitHub/ANTLR grammars repository

**Status**: Viable option, requires grammar file research

---

### Option 3: Custom Parser with PLY

**Description**: Build custom parser using PLY (Python Lex-Yacc).

**Approach**:
1. Define COBOL lexer rules (tokens)
2. Define COBOL parser rules (grammar)
3. Build AST nodes during parsing

**Pros**:
- Full control over parsing logic
- Lightweight (PLY is pure Python)
- Can tailor to exact needs
- No external dependencies beyond PLY

**Cons**:
- Significant development effort
- Need to handle COBOL grammar complexity
- Maintenance burden
- May miss edge cases

**Status**: Viable but time-consuming

---

### Option 4: pycobol (If Available)

**Description**: Python COBOL parser library (if exists).

**Status**: Need to verify existence and availability

**Action**: Search PyPI and GitHub for "pycobol" or "cobol-parser"

---

## Evaluation Criteria

| Criterion | Weight | Cobol-REKT | ANTLR | PLY Custom | Notes |
|-----------|--------|------------|-------|------------|-------|
| Ease of Integration | High | ? | Medium | Low | Need to verify each |
| Maintenance Status | High | ? | High | N/A | ANTLR is mature |
| Documentation | Medium | ? | High | Low | ANTLR well-documented |
| Customization | Medium | Low | Medium | High | Custom = full control |
| Development Time | High | Low | Medium | High | REKT fastest if works |
| COBOL Coverage | High | ? | Medium | Medium | Depends on grammar/rules |
| AST Quality | High | ? | Medium | High | Custom = tailored |

## Recommendation

### Primary Recommendation: ANTLR with COBOL Grammar

**Rationale**:
1. **Mature Technology**: ANTLR is well-established with good Python support
2. **Grammar-Based**: Declarative approach makes grammar easier to understand and modify
3. **Flexibility**: Can customize grammar for specific COBOL dialects or features
4. **Community**: Large community and many existing grammars
5. **Documentation**: Well-documented with good examples

**Implementation Steps**:
1. Search for existing COBOL ANTLR grammar files
2. Evaluate grammar completeness for our needs
3. Generate Python parser using ANTLR4
4. Test with sample COBOL files (`tests/cobol_samples/`)
5. Integrate into project

**Dependencies**:
- `antlr4-python3-runtime` (Python runtime)
- ANTLR4 tool (for generating parser, can use via Docker or install locally)

### Secondary Recommendation: Cobol-REKT (If Python-Compatible)

**Rationale**:
- If Cobol-REKT is Python-based and well-maintained, it could save significant development time
- Already includes CFG capabilities which we need

**Action**: Investigate Cobol-REKT codebase to verify Python compatibility and assess code quality.

### Fallback: Custom PLY Parser

**Rationale**:
- If other options don't work, build custom parser
- Start with basic COBOL constructs and expand
- Full control but more development time

## Test Files Created

Three COBOL test files have been created in `tests/cobol_samples/`:

1. **CUSTOMER-ACCOUNT-MAIN.cbl** - Main program demonstrating:
   - File I/O (FD, SELECT, READ)
   - WORKING-STORAGE variables
   - PERFORM statements
   - CALL statements
   - IF/ELSE conditionals
   - Loop processing (PERFORM UNTIL)

2. **CALCULATE-PENALTY.cbl** - Subprogram demonstrating:
   - LINKAGE SECTION (parameter passing)
   - PROCEDURE DIVISION USING
   - COMPUTE statements
   - EXIT PROGRAM

3. **ACCOUNT-VALIDATOR.cbl** - Subprogram demonstrating:
   - EVALUATE statements
   - Multiple internal procedures
   - 88-level condition names

These files will be used to test parser capabilities.

## Next Steps

1. **Investigate ANTLR COBOL Grammar**
   - Search GitHub for "antlr cobol grammar"
   - Check ANTLR grammars repository
   - Evaluate grammar completeness

2. **Test ANTLR Approach**
   - Install ANTLR4 and Python runtime
   - Generate parser from grammar
   - Test with `tests/cobol_samples/CUSTOMER-ACCOUNT-MAIN.cbl`
   - Evaluate parse tree quality

3. **Investigate Cobol-REKT**
   - Check GitHub repository
   - Verify Python compatibility
   - Assess code quality and maintenance

4. **Decision Point**
   - Choose parser based on testing results
   - Document decision and rationale
   - Proceed to Step 2 (AST Builder Implementation)

## Implementation Notes

### ANTLR Integration Pattern

If using ANTLR:

```python
# src/core/services/cobol_parser_service.py
from antlr4 import FileStream, CommonTokenStream
from cobol_parser.COBOLLexer import COBOLLexer
from cobol_parser.COBOLParser import COBOLParser

def parse_cobol_file(file_path: str) -> COBOLParser.ProgramContext:
    """Parse COBOL file using ANTLR parser."""
    input_stream = FileStream(file_path)
    lexer = COBOLLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = COBOLParser(stream)
    tree = parser.program()
    return tree
```

### PLY Integration Pattern

If using PLY:

```python
# src/core/services/cobol_parser_service.py
import ply.lex as lex
import ply.yacc as yacc
from src.core.models.cobol_analysis import ProgramNode

# Define tokens
tokens = ('IDENTIFICATION', 'DIVISION', 'PROGRAM_ID', ...)

# Define lexer
def t_IDENTIFICATION(t):
    r'IDENTIFICATION'
    return t

# Define parser
def p_program(p):
    'program : identification_division environment_division data_division procedure_division'
    p[0] = ProgramNode(divisions=[p[1], p[2], p[3], p[4]])

# Build parser
parser = yacc.yacc()
```

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-11-07 | **PLY-based Custom Parser** | Selected PLY for initial implementation due to: pure Python (no external tools), full control, extensibility. Parser structure created, needs refinement for COBOL fixed-format and edge cases. |

## Implementation Status

### Completed
- ✅ PLY parser structure created (`src/core/services/cobol_parser_service.py`)
- ✅ Basic grammar rules for COBOL divisions
- ✅ Token definitions for COBOL keywords
- ✅ Parse tree node structure
- ✅ Test files created (`tests/cobol_samples/`)

### In Progress
- ⏳ Parser refinement for COBOL fixed-format (columns 1-72)
- ⏳ Case-insensitivity handling
- ⏳ Testing with sample files
- ⏳ Error handling improvements

### Next Steps
1. Handle COBOL fixed-format (strip columns 1-6, handle column 7 indicators)
2. Make lexer case-insensitive
3. Add more COBOL constructs as needed
4. Test with all sample files
5. Document parser API

## Parser Implementation

**Location**: `src/core/services/cobol_parser_service.py`

**Approach**: PLY (Python Lex-Yacc) - pure Python parser generator

**Status**: Basic structure complete, needs refinement for production use

**Key Features**:
- Handles all four COBOL divisions
- Basic statement parsing (IF, PERFORM, CALL, etc.)
- Parse tree structure suitable for AST construction
- Extensible grammar rules

**Limitations**:
- Currently handles free-format COBOL (needs fixed-format support)
- Case-sensitive (needs case-insensitive handling)
- Some COBOL constructs not yet implemented
- Error messages need improvement

## References

- [ANTLR Official Site](https://www.antlr.org/)
- [ANTLR Python Runtime](https://pypi.org/project/antlr4-python3-runtime/)
- [PLY Documentation](https://www.dabeaz.com/ply/)
- [Cobol-REKT GitHub](https://github.com/avishek-sen-gupta/cobol-rekt)
