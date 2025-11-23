       IDENTIFICATION DIVISION.
       PROGRAM-ID. BATCH-CLEANUP.
       AUTHOR. Test Suite.

      ******************************************************************
      * Batch cleanup program - ISOLATED
      * This program has no dependencies and calls no other programs
      * Used to test detection of isolated programs
      ******************************************************************

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-FILE-COUNTER       PIC 9(10) VALUE ZERO.
       01  WS-CLEANUP-DATE       PIC 9(08).
       01  WS-STATUS-FLAG        PIC X(01).

       PROCEDURE DIVISION.

       CLEANUP-MAIN.
           DISPLAY "Starting Batch Cleanup Process"

           PERFORM CLEANUP-OLD-FILES
           PERFORM CLEANUP-TEMP-DATA
           PERFORM DISPLAY-STATISTICS

           DISPLAY "Batch Cleanup Completed"
           STOP RUN.

       CLEANUP-OLD-FILES.
           DISPLAY "Cleaning old files..."
           ADD 1 TO WS-FILE-COUNTER
           MOVE 20240101 TO WS-CLEANUP-DATE.

       CLEANUP-TEMP-DATA.
           DISPLAY "Cleaning temporary data..."
           ADD 1 TO WS-FILE-COUNTER.

       DISPLAY-STATISTICS.
           DISPLAY "Files cleaned: " WS-FILE-COUNTER
           DISPLAY "Cleanup date: " WS-CLEANUP-DATE.
