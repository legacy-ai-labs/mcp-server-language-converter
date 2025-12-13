       IDENTIFICATION DIVISION.
       PROGRAM-ID. REPORT-GEN.
       AUTHOR. Test Suite.

      ******************************************************************
      * Report generation module
      * Creates various types of reports
      ******************************************************************

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-REPORT-DATE        PIC 9(08).
       01  WS-RECORD-COUNT       PIC 9(10).

       COPY COMMON-DEFS.
       COPY CUSTOMER-REC.

       LINKAGE SECTION.
       01  LS-REPORT-TYPE        PIC X(10).
       01  LS-STATUS             PIC X(01).

       PROCEDURE DIVISION USING LS-REPORT-TYPE
                                LS-STATUS.

       REPORT-MAIN.
           DISPLAY "Generating Report: " LS-REPORT-TYPE

           EVALUATE LS-REPORT-TYPE
               WHEN 'DAILY'
                   PERFORM GENERATE-DAILY-REPORT
               WHEN 'WEEKLY'
                   PERFORM GENERATE-WEEKLY-REPORT
               WHEN 'MONTHLY'
                   PERFORM GENERATE-MONTHLY-REPORT
               WHEN OTHER
                   MOVE 'F' TO LS-STATUS
                   GOBACK
           END-EVALUATE

      * Log report generation
           CALL 'UTILITY-FUNCS' USING
               BY VALUE 'LOG-REPORT'
           END-CALL

           MOVE 'S' TO LS-STATUS
           GOBACK.

       GENERATE-DAILY-REPORT.
           MOVE 20240101 TO WS-REPORT-DATE
           MOVE 100 TO WS-RECORD-COUNT
           DISPLAY "Daily Report Generated".

       GENERATE-WEEKLY-REPORT.
           DISPLAY "Weekly Report Generated".

       GENERATE-MONTHLY-REPORT.
           DISPLAY "Monthly Report Generated".
