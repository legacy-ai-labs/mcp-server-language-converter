       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTOMER-MGMT.
       AUTHOR. Test Suite.

      ******************************************************************
      * Customer management module
      * Handles customer data validation and database operations
      ******************************************************************

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-VALIDATION-FLAG    PIC X(01).
       01  WS-DB-OPERATION       PIC X(10).
       01  WS-AUDIT-FLAG         PIC X(01) VALUE 'Y'.

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
