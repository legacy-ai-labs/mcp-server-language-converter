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
