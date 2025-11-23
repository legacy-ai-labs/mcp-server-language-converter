       IDENTIFICATION DIVISION.
       PROGRAM-ID. DB-ACCESS.
       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-SQL-CODE           PIC S9(9) COMP.
       01  WS-DB-STATUS          PIC X(02).

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
      *> START COPYBOOK: CUSTOMER-REC (from CUSTOMER-REC.cpy)
      ******************************************************************
      * CUSTOMER-REC.cpy
      * Customer record structure
      ******************************************************************
       01  CUSTOMER-RECORD.
           05  CUST-ID               PIC 9(10).
           05  CUST-NAME.
               10  CUST-FIRST-NAME   PIC X(30).
               10  CUST-LAST-NAME    PIC X(30).
           05  CUST-ADDRESS.
               10  CUST-STREET       PIC X(50).
               10  CUST-CITY         PIC X(30).
               10  CUST-STATE        PIC X(02).
               10  CUST-ZIP          PIC 9(05).
           05  CUST-PHONE            PIC X(15).
           05  CUST-EMAIL            PIC X(50).
           05  CUST-STATUS           PIC X(01).
               88  CUST-ACTIVE       VALUE 'A'.
               88  CUST-INACTIVE     VALUE 'I'.
               88  CUST-SUSPENDED    VALUE 'S'.
           05  CUST-CREDIT-LIMIT     PIC 9(10)V99.
           05  CUST-BALANCE          PIC S9(10)V99.
      *> END COPYBOOK: CUSTOMER-REC

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
