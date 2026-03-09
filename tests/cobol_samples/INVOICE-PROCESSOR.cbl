       IDENTIFICATION DIVISION.
       PROGRAM-ID. INVOICE-PROCESSOR.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT INVOICE-FILE ASSIGN TO 'INVOICES.DAT'
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD INVOICE-FILE.
       COPY INVOICE-RECORD.

       WORKING-STORAGE SECTION.
       01 WS-EOF-FLAG                PIC X(1) VALUE 'N'.
           88 END-OF-FILE            VALUE 'Y'.
           88 NOT-END-OF-FILE        VALUE 'N'.
       01 WS-TOTAL-INVOICES          PIC 9(5) VALUE ZERO.
       01 WS-OVERDUE-COUNT           PIC 9(5) VALUE ZERO.
       01 WS-TOTAL-PENALTIES         PIC S9(9)V99 COMP-3 VALUE ZERO.
       01 WS-CURRENT-DATE            PIC X(8).
       01 WS-RETURN-CODE             PIC 9(2) VALUE ZERO.

       PROCEDURE DIVISION.
       MAIN-PROCESSING.
           MOVE FUNCTION CURRENT-DATE(1:8) TO WS-CURRENT-DATE
           DISPLAY 'Starting Invoice Processing: ' WS-CURRENT-DATE
           OPEN INPUT INVOICE-FILE

           PERFORM UNTIL END-OF-FILE
               READ INVOICE-FILE
                   AT END SET END-OF-FILE TO TRUE
                   NOT AT END
                       PERFORM PROCESS-INVOICE
                       ADD 1 TO WS-TOTAL-INVOICES
               END-READ
           END-PERFORM

           CLOSE INVOICE-FILE
           PERFORM PRINT-SUMMARY
           STOP RUN.

       PROCESS-INVOICE.
           EVALUATE TRUE
               WHEN INV-PAID
                   CONTINUE
               WHEN INV-CANCELLED
                   CONTINUE
               WHEN INV-OVERDUE
                   PERFORM HANDLE-OVERDUE-INVOICE
               WHEN INV-PENDING
                   PERFORM CHECK-PENDING-INVOICE
               WHEN OTHER
                   DISPLAY 'Unknown status for invoice: ' INV-ID
           END-EVALUATE.

       HANDLE-OVERDUE-INVOICE.
           ADD 1 TO WS-OVERDUE-COUNT
           CALL 'CALCULATE-PENALTY' USING INV-AMOUNT
                                          INV-PENALTY-AMOUNT

           IF INV-PENALTY-AMOUNT > ZERO
               ADD INV-PENALTY-AMOUNT TO WS-TOTAL-PENALTIES
               DISPLAY 'Penalty applied to invoice ' INV-ID
                   ': ' INV-PENALTY-AMOUNT
           END-IF.

       CHECK-PENDING-INVOICE.
           IF INV-DUE-DATE < WS-CURRENT-DATE
               MOVE 'O' TO INV-STATUS
               PERFORM HANDLE-OVERDUE-INVOICE
           END-IF.

       PRINT-SUMMARY.
           DISPLAY '================================'
           DISPLAY 'Invoice Processing Summary'
           DISPLAY 'Total Invoices  : ' WS-TOTAL-INVOICES
           DISPLAY 'Overdue Invoices: ' WS-OVERDUE-COUNT
           DISPLAY 'Total Penalties : ' WS-TOTAL-PENALTIES
           DISPLAY '================================'.
