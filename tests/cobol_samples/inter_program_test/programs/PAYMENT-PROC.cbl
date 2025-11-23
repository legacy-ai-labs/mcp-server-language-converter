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

      *> START COPYBOOK: COMMON-DEFS (from COMMON-DEFS.cpy)
      ******************************************************************
      * COMMON-DEFS.cpy
      * Common definitions used across multiple programs
      ******************************************************************
       01  COMMON-CONSTANTS.
           05  CC-SUCCESS            PIC X(01) VALUE 'S'.
           05  CC-FAILURE            PIC X(01) VALUE 'F'.
           05  CC-MAX-RETRIES        PIC 9(02) VALUE 03.
           05  CC-TIMEOUT-SECONDS    PIC 9(03) VALUE 030.

       01  COMMON-FLAGS.
           05  CF-DEBUG-MODE         PIC X(01) VALUE 'N'.
           05  CF-TRACE-MODE         PIC X(01) VALUE 'N'.
           05  CF-ERROR-FLAG         PIC X(01) VALUE 'N'.

       01  COMMON-MESSAGES.
           05  CM-SUCCESS-MSG        PIC X(30) VALUE 'Operation completed'.
           05  CM-ERROR-MSG          PIC X(30) VALUE 'Operation failed'.
      *> END COPYBOOK: COMMON-DEFS

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
