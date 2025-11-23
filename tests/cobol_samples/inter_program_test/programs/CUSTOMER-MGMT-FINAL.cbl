       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTOMER-MGMT.
       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-VALIDATION-FLAG    PIC X(01).
       01  WS-DB-OPERATION       PIC X(10).
       01  WS-AUDIT-FLAG         PIC X(01) VALUE 'Y'.


       LINKAGE SECTION.
       01  LS-CUSTOMER-ID        PIC 9(10).
       01  LS-PROCESS-STATUS     PIC X(01).
       01  LS-ERROR-CODE         PIC 9(03).

       PROCEDURE DIVISION USING LS-CUSTOMER-ID
                                LS-PROCESS-STATUS
                                LS-ERROR-CODE.

       CUSTOMER-MAIN.
           DISPLAY "Processing Customer: " LS-CUSTOMER-ID

           PERFORM VALIDATE-CUSTOMER
           IF WS-VALIDATION-FLAG = 'Y'
              PERFORM ACCESS-DATABASE
              PERFORM AUDIT-TRAIL
           END-IF

           MOVE 'S' TO LS-PROCESS-STATUS
           GOBACK.

       VALIDATE-CUSTOMER.
           CALL 'VALIDATE-DATA' USING
               BY VALUE 'CUSTOMER'
               BY VALUE LS-CUSTOMER-ID
               BY REFERENCE WS-VALIDATION-FLAG
           END-CALL.

       ACCESS-DATABASE.
           MOVE 'SELECT' TO WS-DB-OPERATION
           CALL 'DB-ACCESS' USING
               BY VALUE WS-DB-OPERATION
               BY VALUE LS-CUSTOMER-ID
               BY REFERENCE CUSTOMER-RECORD
           END-CALL.

       AUDIT-TRAIL.
           IF WS-AUDIT-FLAG = 'Y'
              CALL 'AUDIT-LOG' USING
                  BY VALUE 'CUSTOMER'
                  BY VALUE LS-CUSTOMER-ID
              END-CALL
           END-IF.
