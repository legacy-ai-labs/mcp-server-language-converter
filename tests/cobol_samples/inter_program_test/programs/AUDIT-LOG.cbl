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

      *> START COPYBOOK: DB-CONFIG (from DB-CONFIG.cpy)
      ******************************************************************
      * DB-CONFIG.cpy
      * Database configuration and connection parameters
      ******************************************************************
       01  DB-CONNECTION-INFO.
           05  DB-HOST               PIC X(50) VALUE 'localhost'.
           05  DB-PORT               PIC 9(05) VALUE 5432.
           05  DB-NAME               PIC X(30) VALUE 'COBOL_TEST_DB'.
           05  DB-USER               PIC X(30) VALUE 'cobol_user'.
           05  DB-PASSWORD           PIC X(30) VALUE 'secure_pass'.

       01  DB-STATUS-CODES.
           05  DB-SUCCESS            PIC X(02) VALUE '00'.
           05  DB-NOT-FOUND          PIC X(02) VALUE '02'.
           05  DB-DUPLICATE          PIC X(02) VALUE '23'.
           05  DB-ERROR              PIC X(02) VALUE '99'.

       01  DB-OPERATION-TYPES.
           05  DB-OP-SELECT          PIC X(10) VALUE 'SELECT'.
           05  DB-OP-INSERT          PIC X(10) VALUE 'INSERT'.
           05  DB-OP-UPDATE          PIC X(10) VALUE 'UPDATE'.
           05  DB-OP-DELETE          PIC X(10) VALUE 'DELETE'.
      *> END COPYBOOK: DB-CONFIG

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
