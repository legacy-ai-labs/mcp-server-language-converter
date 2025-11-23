       IDENTIFICATION DIVISION.
       PROGRAM-ID. VALIDATE-DATA.
       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-VALIDATION-RESULT  PIC X(01).

       COPY COMMON-DEFS.

       LINKAGE SECTION.
       01  LS-DATA-TYPE          PIC X(10).
       01  LS-DATA-VALUE         PIC 9(10).
       01  LS-VALID-FLAG         PIC X(01).

       PROCEDURE DIVISION USING LS-DATA-TYPE
                                LS-DATA-VALUE
                                LS-VALID-FLAG.

       VALIDATE-MAIN.
           DISPLAY "Validating: " LS-DATA-TYPE " Value: " LS-DATA-VALUE

           EVALUATE LS-DATA-TYPE
               WHEN 'CUSTOMER'
                   PERFORM VALIDATE-CUSTOMER-ID
               WHEN 'ORDER'
                   PERFORM VALIDATE-ORDER-ID
               WHEN OTHER
                   MOVE 'N' TO LS-VALID-FLAG
           END-EVALUATE

           GOBACK.

       VALIDATE-CUSTOMER-ID.
           IF LS-DATA-VALUE > 0 AND LS-DATA-VALUE < 99999999
              MOVE 'Y' TO LS-VALID-FLAG
           ELSE
              MOVE 'N' TO LS-VALID-FLAG
           END-IF.

       VALIDATE-ORDER-ID.
           IF LS-DATA-VALUE > 0
              MOVE 'Y' TO LS-VALID-FLAG
           ELSE
              MOVE 'N' TO LS-VALID-FLAG
           END-IF.
