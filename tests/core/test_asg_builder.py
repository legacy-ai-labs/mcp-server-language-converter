"""Tests for the ASG builder service."""

from pathlib import Path

import pytest

from src.core.models.cobol_asg_model import (
    DataDescriptionEntryType,
    ParameterType,
    StatementType,
    UsageType,
)
from src.core.services.cobol_analysis.asg_builder_service import (
    ASGBuilderError,
    build_asg,
    build_asg_from_source,
    build_asg_from_source_with_preprocessing,
    build_asg_with_preprocessing,
)
from src.core.services.cobol_analysis.cobol_parser_antlr_service import ParseNode


# Test fixtures paths
SAMPLES_DIR = Path(__file__).parent.parent / "cobol_samples"
INTER_PROGRAM_DIR = SAMPLES_DIR / "inter_program_test"
PROGRAMS_DIR = INTER_PROGRAM_DIR / "programs"
COPYBOOKS_DIR = INTER_PROGRAM_DIR / "copybooks"


class TestBuildASGFromSource:
    """Tests for build_asg_from_source function."""

    def test_basic_program_structure(self) -> None:
        """Test parsing a basic COBOL program."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST-PROGRAM.
       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY 'Hello World'.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)

        assert program is not None
        assert len(program.compilation_units) == 1

        cu = program.compilation_units[0]
        assert len(cu.program_units) == 1

        pu = cu.program_units[0]
        assert pu.identification_division.program_id == "TEST-PROGRAM"

    def test_data_division_working_storage(self) -> None:
        """Test parsing DATA DIVISION with WORKING-STORAGE."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. DATA-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-COUNTER PIC 9(5) VALUE 0.
       01 WS-NAME    PIC X(50).
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws_entries = pu.data_division.working_storage.entries
        assert len(ws_entries) >= 2

        # Check first entry
        counter_entry = next((e for e in ws_entries if e.name == "WS-COUNTER"), None)
        assert counter_entry is not None
        assert counter_entry.level == 1
        assert counter_entry.picture is not None
        assert "9" in counter_entry.picture.picture_string

    def test_data_division_picture_clause(self) -> None:
        """Test PICTURE clause extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PIC-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-AMOUNT PIC S9(7)V99 COMP-3.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws = pu.data_division.working_storage
        amount_entry = next((e for e in ws.entries if e.name == "WS-AMOUNT"), None)

        assert amount_entry is not None
        assert amount_entry.picture is not None
        assert (
            "S" in amount_entry.picture.picture_string or "s" in amount_entry.picture.picture_string
        )
        assert amount_entry.usage == UsageType.COMP_3

    def test_data_division_occurs_clause(self) -> None:
        """Test OCCURS clause extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. OCCURS-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-TABLE.
          05 WS-ITEM PIC X(10) OCCURS 12 TIMES.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws = pu.data_division.working_storage
        table_entry = next((e for e in ws.entries if e.name == "WS-TABLE"), None)

        assert table_entry is not None
        assert table_entry.entry_type == DataDescriptionEntryType.GROUP
        assert len(table_entry.children) > 0

        item_entry = table_entry.children[0]
        assert item_entry.name == "WS-ITEM"
        assert item_entry.occurs is not None
        assert item_entry.occurs.max_occurs == 12

    def test_data_division_level_88_conditions(self) -> None:
        """Test Level 88 condition extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COND-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-STATUS PIC X VALUE 'A'.
          88 STATUS-ACTIVE VALUE 'A'.
          88 STATUS-INACTIVE VALUE 'I'.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws = pu.data_division.working_storage
        status_entry = next((e for e in ws.entries if e.name == "WS-STATUS"), None)

        assert status_entry is not None
        # Level 88 conditions are children of the data item
        condition_entries = [c for c in status_entry.children if c.level == 88]
        assert len(condition_entries) == 2

    def test_procedure_division_paragraphs(self) -> None:
        """Test PROCEDURE DIVISION paragraph extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PARA-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM PROCESS-PARA.
           STOP RUN.
       PROCESS-PARA.
           DISPLAY 'Processing'.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.procedure_division is not None
        assert len(pu.procedure_division.paragraphs) >= 2

        para_names = [p.paragraph_name for p in pu.procedure_division.paragraphs]
        assert "MAIN-PARA" in para_names

    def test_call_statement_extraction(self) -> None:
        """Test CALL statement extraction with parameters."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CALL-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-PARAM PIC X(10).
       01 WS-RESULT PIC 9(5).
       PROCEDURE DIVISION.
       MAIN-PARA.
           CALL 'SUBPROGRAM' USING BY REFERENCE WS-PARAM
               GIVING WS-RESULT.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.procedure_division is not None

        # Check call statements list
        assert len(pu.procedure_division.call_statements) >= 1

        call_stmt = pu.procedure_division.call_statements[0]
        assert call_stmt.target_program == "SUBPROGRAM"
        assert len(call_stmt.parameters) >= 1
        assert call_stmt.parameters[0].parameter_type == ParameterType.BY_REFERENCE

    def test_perform_statement_types(self) -> None:
        """Test different PERFORM statement types."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PERFORM-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-COUNTER PIC 9(3) VALUE 0.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM PROCESS-PARA.
           PERFORM PROCESS-PARA 5 TIMES.
           STOP RUN.
       PROCESS-PARA.
           ADD 1 TO WS-COUNTER.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.procedure_division is not None

        main_para = next(
            (p for p in pu.procedure_division.paragraphs if p.paragraph_name == "MAIN-PARA"), None
        )
        assert main_para is not None

        perform_stmts = [
            s for s in main_para.statements if s.statement_type == StatementType.PERFORM
        ]
        assert len(perform_stmts) >= 2

    def test_if_statement_extraction(self) -> None:
        """Test IF statement extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. IF-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-BALANCE PIC S9(7)V99.
       PROCEDURE DIVISION.
       MAIN-PARA.
           IF WS-BALANCE < 0
               DISPLAY 'NEGATIVE'
           ELSE
               DISPLAY 'POSITIVE'
           END-IF.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.procedure_division is not None

        main_para = next(
            (p for p in pu.procedure_division.paragraphs if p.paragraph_name == "MAIN-PARA"), None
        )
        assert main_para is not None

        if_stmts = [s for s in main_para.statements if s.statement_type == StatementType.IF]
        assert len(if_stmts) >= 1

        if_stmt = if_stmts[0]
        assert if_stmt.if_details is not None
        assert len(if_stmt.if_details.then_statements) > 0
        assert len(if_stmt.if_details.else_statements) > 0

    def test_evaluate_statement_extraction(self) -> None:
        """Test EVALUATE statement extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. EVAL-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-STATUS PIC X.
       PROCEDURE DIVISION.
       MAIN-PARA.
           EVALUATE WS-STATUS
               WHEN 'A'
                   DISPLAY 'Active'
               WHEN 'I'
                   DISPLAY 'Inactive'
               WHEN OTHER
                   DISPLAY 'Unknown'
           END-EVALUATE.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.procedure_division is not None

        main_para = next(
            (p for p in pu.procedure_division.paragraphs if p.paragraph_name == "MAIN-PARA"), None
        )
        assert main_para is not None

        eval_stmts = [s for s in main_para.statements if s.statement_type == StatementType.EVALUATE]
        assert len(eval_stmts) >= 1

        eval_stmt = eval_stmts[0]
        assert eval_stmt.evaluate_details is not None
        assert len(eval_stmt.evaluate_details.when_clauses) >= 2

    def test_move_statement_extraction(self) -> None:
        """Test MOVE statement extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. MOVE-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-SOURCE PIC X(10).
       01 WS-TARGET PIC X(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           MOVE WS-SOURCE TO WS-TARGET.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.procedure_division is not None

        main_para = next(
            (p for p in pu.procedure_division.paragraphs if p.paragraph_name == "MAIN-PARA"), None
        )
        assert main_para is not None

        move_stmts = [s for s in main_para.statements if s.statement_type == StatementType.MOVE]
        assert len(move_stmts) >= 1

    def test_compute_statement_extraction(self) -> None:
        """Test COMPUTE statement extraction."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COMP-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-A PIC 9(5).
       01 WS-B PIC 9(5).
       01 WS-RESULT PIC 9(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           COMPUTE WS-RESULT = WS-A + WS-B.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.procedure_division is not None

        main_para = next(
            (p for p in pu.procedure_division.paragraphs if p.paragraph_name == "MAIN-PARA"), None
        )
        assert main_para is not None

        compute_stmts = [
            s for s in main_para.statements if s.statement_type == StatementType.COMPUTE
        ]
        assert len(compute_stmts) >= 1


class TestBuildASGErrors:
    """Tests for error handling."""

    def test_invalid_parse_tree_type(self) -> None:
        """Test that non-ParseNode input raises error."""
        with pytest.raises(ASGBuilderError) as exc_info:
            build_asg("not a parse node")  # type: ignore[arg-type]
        assert "ParseNode" in str(exc_info.value)

    def test_invalid_root_node_type(self) -> None:
        """Test that wrong root node type raises error."""
        wrong_root = ParseNode(type="DIVISION", value=None)
        with pytest.raises(ASGBuilderError) as exc_info:
            build_asg(wrong_root)
        assert "PROGRAM" in str(exc_info.value)


class TestExternalCallsExtraction:
    """Tests for external calls extraction."""

    def test_external_calls_list(self) -> None:
        """Test that external calls are properly extracted."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CALL-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           CALL 'PROGRAM-A'.
           CALL 'PROGRAM-B'.
           CALL 'PROGRAM-A'.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)

        # External calls should be deduplicated
        assert "PROGRAM-A" in program.external_calls
        assert "PROGRAM-B" in program.external_calls


class TestComprehensiveProgram:
    """Test with comprehensive COBOL program."""

    def test_comprehensive_program(self) -> None:
        """Test parsing comprehensive COBOL program with all features."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COMPREHENSIVE-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-CUSTOMER-RECORD.
          05 WS-CUST-ID       PIC 9(10).
          05 WS-CUST-NAME     PIC X(50).
          05 WS-CUST-BALANCE  PIC S9(7)V99 COMP-3.
          05 WS-CUST-STATUS   PIC X VALUE 'A'.
             88 ACTIVE-CUST   VALUE 'A'.
             88 INACTIVE-CUST VALUE 'I'.
          05 WS-ORDER-COUNT   PIC 9(5) OCCURS 12 TIMES.
       01 WS-TOTALS.
          05 WS-TOTAL-AMT     PIC 9(10)V99.
          05 WS-COUNTER       PIC 9(5).
       LINKAGE SECTION.
       01 LS-INPUT-PARAM      PIC X(100).
       PROCEDURE DIVISION USING LS-INPUT-PARAM.
       MAIN-PARA.
           PERFORM INITIALIZE-DATA.
           PERFORM PROCESS-DATA 5 TIMES.
           CALL 'SUBPROGRAM' USING BY REFERENCE WS-CUSTOMER-RECORD.
           IF ACTIVE-CUST
               DISPLAY 'Customer is active'
           ELSE
               DISPLAY 'Customer is inactive'
           END-IF.
           EVALUATE WS-CUST-STATUS
               WHEN 'A'
                   MOVE 'Active' TO WS-CUST-NAME
               WHEN 'I'
                   MOVE 'Inactive' TO WS-CUST-NAME
               WHEN OTHER
                   MOVE 'Unknown' TO WS-CUST-NAME
           END-EVALUATE.
           STOP RUN.
       INITIALIZE-DATA.
           INITIALIZE WS-CUSTOMER-RECORD.
           MOVE ZEROS TO WS-TOTALS.
       PROCESS-DATA.
           ADD 1 TO WS-COUNTER.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        # Check identification division
        assert pu.identification_division.program_id == "COMPREHENSIVE-TEST"

        # Check data division
        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None
        assert pu.data_division.linkage_section is not None

        # Check USING clause
        assert pu.procedure_division is not None
        assert len(pu.procedure_division.using_parameters) > 0

        # Check paragraphs
        assert len(pu.procedure_division.paragraphs) >= 3

        # Check call statements
        assert len(pu.procedure_division.call_statements) >= 1
        assert pu.procedure_division.call_statements[0].target_program == "SUBPROGRAM"


class TestDataItemCrossReferences:
    """Tests for data item cross-references (calls list)."""

    def test_move_statement_cross_references(self) -> None:
        """Test that MOVE statements generate cross-references."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. XREF-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-SOURCE PIC X(10).
       01 WS-TARGET PIC X(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           MOVE WS-SOURCE TO WS-TARGET.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        # Find the data entries
        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws = pu.data_division.working_storage
        source_entry = next((e for e in ws.entries if e.name == "WS-SOURCE"), None)
        target_entry = next((e for e in ws.entries if e.name == "WS-TARGET"), None)

        assert source_entry is not None
        assert target_entry is not None

        # WS-SOURCE should have a read reference
        assert len(source_entry.calls) > 0
        source_call = source_entry.calls[0]
        assert source_call.is_read is True
        assert source_call.is_write is False

        # WS-TARGET should have a write reference
        assert len(target_entry.calls) > 0
        target_call = target_entry.calls[0]
        assert target_call.is_read is False
        assert target_call.is_write is True

    def test_compute_statement_cross_references(self) -> None:
        """Test that COMPUTE statements generate cross-references."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. XREF-COMPUTE.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-A PIC 9(5).
       01 WS-B PIC 9(5).
       01 WS-RESULT PIC 9(10).
       PROCEDURE DIVISION.
       MAIN-PARA.
           COMPUTE WS-RESULT = WS-A + WS-B.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws = pu.data_division.working_storage
        result_entry = next((e for e in ws.entries if e.name == "WS-RESULT"), None)
        a_entry = next((e for e in ws.entries if e.name == "WS-A"), None)

        assert result_entry is not None
        assert a_entry is not None

        # WS-RESULT should have a write reference
        assert len(result_entry.calls) > 0
        assert any(c.is_write for c in result_entry.calls)

        # WS-A should have a read reference
        assert len(a_entry.calls) > 0
        assert any(c.is_read for c in a_entry.calls)

    def test_add_statement_cross_references(self) -> None:
        """Test that ADD statements generate cross-references."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. XREF-ADD.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-COUNTER PIC 9(5) VALUE 0.
       PROCEDURE DIVISION.
       MAIN-PARA.
           ADD 1 TO WS-COUNTER.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws = pu.data_division.working_storage
        counter_entry = next((e for e in ws.entries if e.name == "WS-COUNTER"), None)

        assert counter_entry is not None

        # WS-COUNTER should have references from ADD statement
        # (appears in operands - both as read operand and as target)
        assert len(counter_entry.calls) > 0
        assert any(c.is_read for c in counter_entry.calls)

    def test_call_statement_cross_references(self) -> None:
        """Test that CALL statements generate cross-references for parameters."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. XREF-CALL.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-PARAM PIC X(10).
       01 WS-RESULT PIC 9(5).
       PROCEDURE DIVISION.
       MAIN-PARA.
           CALL 'SUBPROGRAM' USING BY REFERENCE WS-PARAM
               GIVING WS-RESULT.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]

        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        ws = pu.data_division.working_storage
        param_entry = next((e for e in ws.entries if e.name == "WS-PARAM"), None)
        result_entry = next((e for e in ws.entries if e.name == "WS-RESULT"), None)

        assert param_entry is not None
        assert result_entry is not None

        # WS-PARAM is BY REFERENCE - should be read/write
        assert len(param_entry.calls) > 0
        param_call = param_entry.calls[0]
        assert param_call.is_read is True
        assert param_call.is_write is True  # BY REFERENCE can modify

        # WS-RESULT is GIVING - should be write only
        assert len(result_entry.calls) > 0
        result_call = result_entry.calls[0]
        assert result_call.is_write is True


class TestParagraphCrossReferences:
    """Tests for paragraph cross-references (who performs each paragraph)."""

    def test_simple_perform_cross_references(self) -> None:
        """Test that PERFORM statements generate paragraph cross-references."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PERFORM-TEST.
       PROCEDURE DIVISION.
       MAIN-PARAGRAPH.
           PERFORM INIT-PARAGRAPH.
           PERFORM PROCESS-DATA.
           STOP RUN.
       INIT-PARAGRAPH.
           DISPLAY 'INIT'.
       PROCESS-DATA.
           DISPLAY 'PROCESS'.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division
        assert proc is not None

        # Find paragraphs
        main_para = next((p for p in proc.paragraphs if p.name == "MAIN-PARAGRAPH"), None)
        init_para = next((p for p in proc.paragraphs if p.name == "INIT-PARAGRAPH"), None)
        process_para = next((p for p in proc.paragraphs if p.name == "PROCESS-DATA"), None)

        assert main_para is not None
        assert init_para is not None
        assert process_para is not None

        # MAIN-PARAGRAPH calls INIT-PARAGRAPH and PROCESS-DATA
        assert "INIT-PARAGRAPH" in main_para.calls_to
        assert "PROCESS-DATA" in main_para.calls_to
        assert len(main_para.called_by) == 0  # Nobody calls MAIN

        # INIT-PARAGRAPH is called by MAIN-PARAGRAPH
        assert "MAIN-PARAGRAPH" in init_para.called_by
        assert len(init_para.calls) > 0
        assert any("MAIN-PARAGRAPH" in c.name for c in init_para.calls)

        # PROCESS-DATA is called by MAIN-PARAGRAPH
        assert "MAIN-PARAGRAPH" in process_para.called_by
        assert len(process_para.calls) > 0

    def test_chained_perform_cross_references(self) -> None:
        """Test cross-references with chained PERFORM calls."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CHAIN-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM LEVEL-1.
           STOP RUN.
       LEVEL-1.
           PERFORM LEVEL-2.
       LEVEL-2.
           PERFORM LEVEL-3.
       LEVEL-3.
           DISPLAY 'DONE'.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division
        assert proc is not None

        level1 = next((p for p in proc.paragraphs if p.name == "LEVEL-1"), None)
        level2 = next((p for p in proc.paragraphs if p.name == "LEVEL-2"), None)
        level3 = next((p for p in proc.paragraphs if p.name == "LEVEL-3"), None)

        assert level1 is not None
        assert level2 is not None
        assert level3 is not None

        # LEVEL-1 is called by MAIN-PARA, calls LEVEL-2
        assert "MAIN-PARA" in level1.called_by
        assert "LEVEL-2" in level1.calls_to

        # LEVEL-2 is called by LEVEL-1, calls LEVEL-3
        assert "LEVEL-1" in level2.called_by
        assert "LEVEL-3" in level2.calls_to

        # LEVEL-3 is called by LEVEL-2, calls nothing
        assert "LEVEL-2" in level3.called_by
        assert len(level3.calls_to) == 0

    def test_perform_thru_cross_references(self) -> None:
        """Test cross-references with PERFORM THRU clause."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. THRU-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM PARA-A THRU PARA-C.
           STOP RUN.
       PARA-A.
           DISPLAY 'A'.
       PARA-B.
           DISPLAY 'B'.
       PARA-C.
           DISPLAY 'C'.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division
        assert proc is not None

        para_a = next((p for p in proc.paragraphs if p.name == "PARA-A"), None)
        para_c = next((p for p in proc.paragraphs if p.name == "PARA-C"), None)

        assert para_a is not None
        assert para_c is not None

        # PARA-A is the PERFORM target
        assert "MAIN-PARA" in para_a.called_by
        assert any("PERFORM from" in c.name for c in para_a.calls)

        # PARA-C is the THRU target
        assert "MAIN-PARA" in para_c.called_by
        assert any("PERFORM THRU from" in c.name for c in para_c.calls)

    def test_perform_without_data_division(self) -> None:
        """Test that paragraph cross-references work without DATA DIVISION."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. NO-DATA-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM SUB-PARA.
           STOP RUN.
       SUB-PARA.
           DISPLAY 'HELLO'.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division
        assert proc is not None

        # Should still have cross-references even without DATA DIVISION
        sub_para = next((p for p in proc.paragraphs if p.name == "SUB-PARA"), None)
        assert sub_para is not None
        assert "MAIN-PARA" in sub_para.called_by
        assert len(sub_para.calls) > 0

    def test_perform_inside_if_statement(self) -> None:
        """Test that PERFORM inside IF statements generates cross-references."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. IF-PERFORM-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           IF 1 = 1
               PERFORM SUB-A
           ELSE
               PERFORM SUB-B
           END-IF.
           STOP RUN.
       SUB-A.
           DISPLAY 'A'.
       SUB-B.
           DISPLAY 'B'.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division
        assert proc is not None

        sub_a = next((p for p in proc.paragraphs if p.name == "SUB-A"), None)
        sub_b = next((p for p in proc.paragraphs if p.name == "SUB-B"), None)

        assert sub_a is not None
        assert sub_b is not None

        # Both should be called by MAIN-PARA (from within IF branches)
        assert "MAIN-PARA" in sub_a.called_by
        assert "MAIN-PARA" in sub_b.called_by


class TestSectionCrossReferences:
    """Tests for section cross-references (who PERFORMs each section)."""

    def test_simple_section_cross_references(self) -> None:
        """Test that PERFORM on sections generates cross-references."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SECTION-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM SUB-SECTION.
           STOP RUN.
       SUB-SECTION SECTION.
       SUB-PARA.
           DISPLAY HELLO.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division

        assert proc is not None

        # Verify section was built
        assert len(proc.sections) == 1
        sub_section = proc.sections[0]
        assert sub_section.name == "SUB-SECTION"

        # Section should be called by MAIN-PARA
        assert "MAIN-PARA" in sub_section.called_by
        assert len(sub_section.calls) > 0
        assert any("MAIN-PARA" in c.name for c in sub_section.calls)

        # MAIN-PARA should have SUB-SECTION in calls_to
        main_para = proc.paragraphs[0]
        assert "SUB-SECTION" in main_para.calls_to

    def test_chained_section_cross_references(self) -> None:
        """Test cross-references with chained section calls."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CHAIN-SECTION.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM INIT-SECTION.
           STOP RUN.
       INIT-SECTION SECTION.
       INIT-PARA.
           PERFORM PROCESS-SECTION.
       PROCESS-SECTION SECTION.
       PROCESS-PARA.
           DISPLAY DONE.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division

        assert proc is not None

        # Find sections
        init_section = next((s for s in proc.sections if s.name == "INIT-SECTION"), None)
        process_section = next((s for s in proc.sections if s.name == "PROCESS-SECTION"), None)

        assert init_section is not None
        assert process_section is not None

        # INIT-SECTION called by MAIN-PARA, calls PROCESS-SECTION
        assert "MAIN-PARA" in init_section.called_by
        assert "PROCESS-SECTION" in init_section.calls_to

        # PROCESS-SECTION called by INIT-PARA (inside INIT-SECTION)
        assert "INIT-PARA" in process_section.called_by

    def test_section_with_multiple_callers(self) -> None:
        """Test section called by multiple paragraphs."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. MULTI-CALLER.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM SHARED-SECTION.
           STOP RUN.
       PROCESS-SECTION SECTION.
       PROCESS-PARA.
           PERFORM SHARED-SECTION.
       SHARED-SECTION SECTION.
       SHARED-PARA.
           DISPLAY SHARED-MSG.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division

        assert proc is not None

        # Find SHARED-SECTION
        shared_section = next((s for s in proc.sections if s.name == "SHARED-SECTION"), None)
        assert shared_section is not None

        # Should be called by both MAIN-PARA and PROCESS-PARA
        assert "MAIN-PARA" in shared_section.called_by
        assert "PROCESS-PARA" in shared_section.called_by
        assert len(shared_section.calls) == 2

    def test_section_paragraphs_separated(self) -> None:
        """Test that top-level paragraphs and section paragraphs are properly separated."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SEPARATE-TEST.
       PROCEDURE DIVISION.
       TOP-PARA-1.
           DISPLAY ONE.
       TOP-PARA-2.
           DISPLAY TWO.
       MY-SECTION SECTION.
       SECTION-PARA-1.
           DISPLAY THREE.
       SECTION-PARA-2.
           DISPLAY FOUR.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division

        assert proc is not None

        # Top-level paragraphs should only include TOP-PARA-1 and TOP-PARA-2
        top_para_names = [p.name for p in proc.paragraphs]
        assert "TOP-PARA-1" in top_para_names
        assert "TOP-PARA-2" in top_para_names
        assert "SECTION-PARA-1" not in top_para_names
        assert "SECTION-PARA-2" not in top_para_names

        # Section paragraphs should be inside the section
        assert len(proc.sections) == 1
        section = proc.sections[0]
        section_para_names = [p.name for p in section.paragraphs]
        assert "SECTION-PARA-1" in section_para_names
        assert "SECTION-PARA-2" in section_para_names

        # All paragraphs should include everything
        all_para_names = [p.name for p in proc.all_paragraphs]
        assert len(all_para_names) == 4

    def test_called_by_count(self) -> None:
        """Test that called_by_count is populated correctly for sections."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COUNT-TEST.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM SUB-SECTION.
           STOP RUN.
       OTHER-PARA.
           PERFORM SUB-SECTION.
       THIRD-PARA.
           PERFORM SUB-SECTION.
       SUB-SECTION SECTION.
       SUB-PARA.
           DISPLAY HELLO.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division

        assert proc is not None

        # SUB-SECTION should be called by 3 paragraphs
        sub_section = proc.sections[0]
        assert sub_section.name == "SUB-SECTION"
        assert sub_section.called_by_count == 3
        assert len(sub_section.called_by) == 3


class TestCalledByCount:
    """Tests for called_by_count field on paragraphs and sections."""

    def test_paragraph_called_by_count(self) -> None:
        """Test that called_by_count is populated correctly for paragraphs."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PARA-COUNT.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM TARGET-PARA.
           PERFORM TARGET-PARA.
           STOP RUN.
       CALLER-2.
           PERFORM TARGET-PARA.
       TARGET-PARA.
           DISPLAY HELLO.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division

        assert proc is not None

        # Find TARGET-PARA
        target = next((p for p in proc.paragraphs if p.name == "TARGET-PARA"), None)
        assert target is not None

        # Should be called by 2 unique callers (MAIN-PARA and CALLER-2)
        assert target.called_by_count == 2
        assert len(target.called_by) == 2
        assert "MAIN-PARA" in target.called_by
        assert "CALLER-2" in target.called_by

        # MAIN-PARA should have 0 callers
        main = next((p for p in proc.paragraphs if p.name == "MAIN-PARA"), None)
        assert main is not None
        assert main.called_by_count == 0

    def test_paragraph_in_section_called_by_count(self) -> None:
        """Test called_by_count for paragraphs inside sections."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SECT-PARA-COUNT.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM SECT-PARA.
           STOP RUN.
       MY-SECTION SECTION.
       SECT-PARA.
           DISPLAY HELLO.
       OTHER-PARA.
           PERFORM SECT-PARA.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        proc = pu.procedure_division

        assert proc is not None

        # Find SECT-PARA inside MY-SECTION
        section = proc.sections[0]
        sect_para = next((p for p in section.paragraphs if p.name == "SECT-PARA"), None)
        assert sect_para is not None

        # Should be called by 2 unique callers
        assert sect_para.called_by_count == 2
        assert "MAIN-PARA" in sect_para.called_by
        assert "OTHER-PARA" in sect_para.called_by


class TestIdentificationDivision:
    """Tests for IDENTIFICATION DIVISION metadata extraction."""

    def test_identification_division_metadata(self) -> None:
        """Test extraction of AUTHOR, INSTALLATION, DATE-WRITTEN, etc."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. META-TEST.
       AUTHOR. John Smith.
       INSTALLATION. Main Data Center.
       DATE-WRITTEN. December 2025.
       DATE-COMPILED. 2025-12-11.
       SECURITY. Confidential.
       REMARKS. Test program for metadata.
       PROCEDURE DIVISION.
       MAIN-PARA.
           DISPLAY HELLO.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        id_div = pu.identification_division

        assert id_div.program_id == "META-TEST"
        assert id_div.author == "John Smith."
        assert id_div.installation == "Main Data Center."
        assert id_div.date_written == "December 2025."
        assert id_div.date_compiled == "2025-12-11."
        assert id_div.security == "Confidential."
        assert id_div.remarks == "Test program for metadata."

    def test_identification_division_partial_metadata(self) -> None:
        """Test extraction when only some metadata fields are present."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PARTIAL-META.
       AUTHOR. Jane Doe.
       DATE-WRITTEN. 2025-01-01.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        id_div = pu.identification_division

        assert id_div.program_id == "PARTIAL-META"
        assert id_div.author == "Jane Doe."
        assert id_div.date_written == "2025-01-01."
        # Fields not present should be None
        assert id_div.installation is None
        assert id_div.date_compiled is None
        assert id_div.security is None
        assert id_div.remarks is None

    def test_identification_division_no_metadata(self) -> None:
        """Test when no optional metadata is present."""
        source_code = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. NO-META.
       PROCEDURE DIVISION.
       MAIN-PARA.
           STOP RUN.
"""
        program = build_asg_from_source(source_code)
        pu = program.compilation_units[0].program_units[0]
        id_div = pu.identification_division

        assert id_div.program_id == "NO-META"
        assert id_div.author is None
        assert id_div.installation is None
        assert id_div.date_written is None
        assert id_div.date_compiled is None
        assert id_div.security is None
        assert id_div.remarks is None


@pytest.mark.skipif(
    not PROGRAMS_DIR.exists(),
    reason="Test programs not available",
)
class TestBuildASGWithPreprocessing:
    """Tests for build_asg_with_preprocessing function."""

    def test_asg_with_copybook_expansion(self) -> None:
        """Test building ASG with COPY statement expansion."""
        file_path = PROGRAMS_DIR / "CUSTOMER-MGMT.cbl"

        if not file_path.exists():
            pytest.skip("CUSTOMER-MGMT.cbl not available")

        program, preprocessed = build_asg_with_preprocessing(
            str(file_path),
            copybook_directories=[str(COPYBOOKS_DIR)],
        )

        # Check program was built
        assert program is not None
        assert len(program.compilation_units) == 1

        pu = program.compilation_units[0].program_units[0]
        assert pu.identification_division.program_id == "CUSTOMER-MGMT"

        # Check copybook usages were tracked
        assert len(preprocessed.copybook_usages) >= 2

        # Check specific copybooks
        copybook_names = [u.copybook_name for u in preprocessed.copybook_usages]
        assert "CUSTOMER-REC" in copybook_names
        assert "DB-CONFIG" in copybook_names

        # Check copybooks were resolved
        for usage in preprocessed.copybook_usages:
            if usage.copybook_name in ["CUSTOMER-REC", "DB-CONFIG"]:
                assert usage.is_resolved is True

        # Check copybook info was added to program
        assert len(program.copybook_usages) >= 2

    def test_asg_with_expanded_data_definitions(self) -> None:
        """Test that copybook data definitions appear in ASG."""
        file_path = PROGRAMS_DIR / "CUSTOMER-MGMT.cbl"

        if not file_path.exists():
            pytest.skip("CUSTOMER-MGMT.cbl not available")

        program, _preprocessed = build_asg_with_preprocessing(
            str(file_path),
            copybook_directories=[str(COPYBOOKS_DIR)],
        )

        pu = program.compilation_units[0].program_units[0]

        # Check data division has entries from copybooks
        assert pu.data_division is not None
        assert pu.data_division.working_storage is not None

        # Find CUSTOMER-RECORD from CUSTOMER-REC.cpy
        entries = pu.data_division.working_storage.entries
        entry_names = [e.name for e in entries]

        # The CUSTOMER-RECORD should be present after copybook expansion
        assert "CUSTOMER-RECORD" in entry_names

    def test_asg_with_unresolved_copybook(self) -> None:
        """Test handling of unresolved copybooks."""
        source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. UNRESOLVED-TEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY NONEXISTENT-COPYBOOK.
       PROCEDURE DIVISION.
           STOP RUN.
"""
        # Write to temp file would be needed for full test
        # For now, test with source preprocessing
        _program, preprocessed = build_asg_from_source_with_preprocessing(source)

        assert len(preprocessed.copybook_usages) == 1
        assert preprocessed.copybook_usages[0].copybook_name == "NONEXISTENT-COPYBOOK"
        assert preprocessed.copybook_usages[0].is_resolved is False
        assert preprocessed.has_errors
