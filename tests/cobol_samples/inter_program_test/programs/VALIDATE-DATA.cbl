       IDENTIFICATION DIVISION.
       PROGRAM-ID. VALIDATE-DATA.
       AUTHOR. Test Suite.

      ******************************************************************
      * Data validation module
      * Validates various types of data
      ******************************************************************

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-VALIDATION-RESULT  PIC X(01).

      *> START COPYBOOK: COMMON-DEFS (from COMMON-DEFS.cpy)
      ******************************************************************
      * COMMON-DEFS.cpy
      * Common definitions used across multiple programs
      ******************************************************************
       01  COMMON-CONSTANTS.
           05  CC-SUCCESS            PIC X(01) VALUE 'S'.
           05  CC-FAILURE            PIC X(01) VALUE 'F'.
           05  CC-MAX-RETRIES        PIC 9(02) VALUE 03.
           05  CC-TIMEOUT-SECONDS    PIC 9(03) VALUE 030.

       01  COMMON-FLAGS.
           05  CF-DEBUG-MODE         PIC X(01) VALUE 'N'.
           05  CF-TRACE-MODE         PIC X(01) VALUE 'N'.
           05  CF-ERROR-FLAG         PIC X(01) VALUE 'N'.

       01  COMMON-MESSAGES.
           05  CM-SUCCESS-MSG        PIC X(30) VALUE 'Operation completed'.
           05  CM-ERROR-MSG          PIC X(30) VALUE 'Operation failed'.
      *> END COPYBOOK: COMMON-DEFS

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
