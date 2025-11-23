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
