       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYMENT-PROC.
       AUTHOR. Test Suite.

      ******************************************************************
      * Payment processing module
      * Handles payment transactions
      ******************************************************************

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-TRANSACTION-ID     PIC 9(15).
       01  WS-DB-OPERATION       PIC X(10).
       01  WS-DB-RESULT          PIC X(200).

       COPY COMMON-DEFS.

       LINKAGE SECTION.
       01  LS-ORDER-ID           PIC 9(10).
       01  LS-AMOUNT             PIC 9(10)V99.
       01  LS-STATUS             PIC X(01).

       PROCEDURE DIVISION USING LS-ORDER-ID
                                LS-AMOUNT
                                LS-STATUS.

       PAYMENT-MAIN.
           DISPLAY "Processing Payment for Order: " LS-ORDER-ID
           DISPLAY "Amount: " LS-AMOUNT

           PERFORM PROCESS-TRANSACTION
           PERFORM UPDATE-DATABASE

           MOVE 'S' TO LS-STATUS
           GOBACK.

       PROCESS-TRANSACTION.
           MOVE 123456789012345 TO WS-TRANSACTION-ID.

       UPDATE-DATABASE.
           MOVE 'UPDATE' TO WS-DB-OPERATION
           CALL 'DB-ACCESS' USING
               BY VALUE WS-DB-OPERATION
               BY VALUE LS-ORDER-ID
               BY REFERENCE WS-DB-RESULT
           END-CALL.
