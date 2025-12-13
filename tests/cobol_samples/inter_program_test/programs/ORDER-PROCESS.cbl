       IDENTIFICATION DIVISION.
       PROGRAM-ID. ORDER-PROCESS.
       AUTHOR. Test Suite.

      ******************************************************************
      * Order processing module
      * Manages order validation, inventory, and payment
      ******************************************************************

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-INVENTORY-STATUS   PIC X(01).
       01  WS-PAYMENT-STATUS     PIC X(01).
       01  WS-ITEM-CODE          PIC X(10).
       01  WS-AMOUNT             PIC 9(10)V99.

       COPY COMMON-DEFS.

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
