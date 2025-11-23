       IDENTIFICATION DIVISION.
       PROGRAM-ID. DB-ACCESS.
       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-SQL-CODE           PIC S9(9) COMP.
       01  WS-DB-STATUS          PIC X(02).

       COPY DB-CONFIG.
       COPY CUSTOMER-REC.

       LINKAGE SECTION.
       01  LS-OPERATION          PIC X(10).
       01  LS-KEY-VALUE          PIC 9(10).
       01  LS-DATA-RECORD        PIC X(200).

       PROCEDURE DIVISION USING LS-OPERATION
                                LS-KEY-VALUE
                                LS-DATA-RECORD.

       DB-MAIN.
           DISPLAY "DB Operation: " LS-OPERATION " Key: " LS-KEY-VALUE

           EVALUATE LS-OPERATION
               WHEN 'SELECT'
                   PERFORM SELECT-RECORD
               WHEN 'INSERT'
                   PERFORM INSERT-RECORD
               WHEN 'UPDATE'
                   PERFORM UPDATE-RECORD
               WHEN 'DELETE'
                   PERFORM DELETE-RECORD
               WHEN OTHER
                   MOVE '99' TO WS-DB-STATUS
           END-EVALUATE

           * This creates a circular reference - DB-ACCESS calls AUDIT-LOG
           * which in turn might call DB-ACCESS for logging
           IF WS-DB-STATUS NOT = '00'
              CALL 'AUDIT-LOG' USING
                  BY VALUE 'DB-ERROR'
                  BY VALUE LS-KEY-VALUE
              END-CALL
           END-IF

           GOBACK.

       SELECT-RECORD.
           MOVE '00' TO WS-DB-STATUS
           MOVE 'Sample Customer Data' TO LS-DATA-RECORD.

       INSERT-RECORD.
           MOVE '00' TO WS-DB-STATUS.

       UPDATE-RECORD.
           MOVE '00' TO WS-DB-STATUS.

       DELETE-RECORD.
           MOVE '00' TO WS-DB-STATUS.
