       IDENTIFICATION DIVISION.
       PROGRAM-ID. AUDIT-LOG.
       AUTHOR. Test Suite.

      ******************************************************************
      * Audit logging module
      * Creates audit trail - has circular dependency with DB-ACCESS
      ******************************************************************

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-AUDIT-RECORD       PIC X(200).
       01  WS-AUDIT-ID           PIC 9(10).
       01  WS-DB-OPERATION       PIC X(10).

       COPY DB-CONFIG.

       LINKAGE SECTION.
       01  LS-AUDIT-TYPE         PIC X(10).
       01  LS-RECORD-ID          PIC 9(10).

       PROCEDURE DIVISION USING LS-AUDIT-TYPE
                                LS-RECORD-ID.

       AUDIT-MAIN.
           DISPLAY "Audit Log: " LS-AUDIT-TYPE " ID: " LS-RECORD-ID

           PERFORM BUILD-AUDIT-RECORD

           * Only write to DB if not a DB-ERROR to avoid infinite loop
           IF LS-AUDIT-TYPE NOT = 'DB-ERROR'
              PERFORM WRITE-TO-DATABASE
           END-IF

           GOBACK.

       BUILD-AUDIT-RECORD.
           STRING LS-AUDIT-TYPE DELIMITED BY SPACE
                  '|' DELIMITED BY SIZE
                  LS-RECORD-ID DELIMITED BY SIZE
                  INTO WS-AUDIT-RECORD
           END-STRING.

       WRITE-TO-DATABASE.
           MOVE 99999 TO WS-AUDIT-ID
           MOVE 'INSERT' TO WS-DB-OPERATION

           * This creates circular dependency: AUDIT-LOG -> DB-ACCESS -> AUDIT-LOG
           CALL 'DB-ACCESS' USING
               BY VALUE WS-DB-OPERATION
               BY VALUE WS-AUDIT-ID
               BY REFERENCE WS-AUDIT-RECORD
           END-CALL.
