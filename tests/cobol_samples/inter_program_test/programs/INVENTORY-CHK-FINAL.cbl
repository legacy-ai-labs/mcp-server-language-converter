       IDENTIFICATION DIVISION.
       PROGRAM-ID. INVENTORY-CHK.
       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-STOCK-LEVEL        PIC 9(10).
       01  WS-DB-OPERATION       PIC X(10).

       LINKAGE SECTION.
       01  LS-ITEM-CODE          PIC X(10).
       01  LS-ORDER-ID           PIC 9(10).
       01  LS-STATUS             PIC X(01).

       PROCEDURE DIVISION USING LS-ITEM-CODE
                                LS-ORDER-ID
                                LS-STATUS.

       INVENTORY-MAIN.
           DISPLAY "Checking Inventory for: " LS-ITEM-CODE

           * Access database to check stock
           MOVE 'SELECT' TO WS-DB-OPERATION
           CALL 'DB-ACCESS' USING
               BY VALUE WS-DB-OPERATION
               BY VALUE LS-ORDER-ID
               BY REFERENCE WS-STOCK-LEVEL
           END-CALL

           IF WS-STOCK-LEVEL > 0
              MOVE 'A' TO LS-STATUS  *> Available
           ELSE
              MOVE 'N' TO LS-STATUS  *> Not available
           END-IF

           GOBACK.
