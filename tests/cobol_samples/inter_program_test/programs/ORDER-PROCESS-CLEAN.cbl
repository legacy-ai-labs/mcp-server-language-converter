       IDENTIFICATION DIVISION.
       PROGRAM-ID. ORDER-PROCESS.
       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-INVENTORY-STATUS   PIC X(01).
       01  WS-PAYMENT-STATUS     PIC X(01).
       01  WS-ITEM-CODE          PIC X(10).
       01  WS-AMOUNT             PIC 9(10)V99.

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
       01  LS-PROCESS-STATUS     PIC X(01).

       PROCEDURE DIVISION USING LS-ORDER-ID
                                LS-PROCESS-STATUS.

       ORDER-MAIN.
           DISPLAY "Processing Order: " LS-ORDER-ID

           PERFORM CHECK-INVENTORY
           IF WS-INVENTORY-STATUS = 'A'
              PERFORM PROCESS-PAYMENT
           END-IF

           IF WS-PAYMENT-STATUS = 'S'
              MOVE 'S' TO LS-PROCESS-STATUS
           ELSE
              MOVE 'F' TO LS-PROCESS-STATUS
           END-IF

           GOBACK.

       CHECK-INVENTORY.
           MOVE 'ITEM001' TO WS-ITEM-CODE
           CALL 'INVENTORY-CHK' USING
               BY VALUE WS-ITEM-CODE
               BY VALUE LS-ORDER-ID
               BY REFERENCE WS-INVENTORY-STATUS
           END-CALL.

       PROCESS-PAYMENT.
           MOVE 1500.00 TO WS-AMOUNT
           CALL 'PAYMENT-PROC' USING
               BY VALUE LS-ORDER-ID
               BY VALUE WS-AMOUNT
               BY REFERENCE WS-PAYMENT-STATUS
           END-CALL.

           * Call utility function for order logging
           CALL 'UTILITY-FUNCS' USING
               BY VALUE 'LOG-ORDER'
           END-CALL.
