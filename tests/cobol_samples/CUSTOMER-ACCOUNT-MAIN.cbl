       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTOMER-ACCOUNT-MAIN.
       AUTHOR. Test Suite.
       DATE-WRITTEN. 2024.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT CUSTOMER-FILE ASSIGN TO 'CUSTOMERS.DAT'
               ORGANIZATION IS SEQUENTIAL
               ACCESS MODE IS SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD CUSTOMER-FILE.
       01 CUSTOMER-RECORD.
           05 CUSTOMER-ID        PIC X(10).
           05 CUSTOMER-NAME      PIC X(50).
           05 ACCOUNT-BALANCE    PIC S9(9)V99 COMP-3.
           05 ACCOUNT-STATUS     PIC X(1).

       WORKING-STORAGE SECTION.
       01 WS-CUSTOMER-ID         PIC X(10).
       01 WS-CUSTOMER-NAME       PIC X(50).
       01 WS-ACCOUNT-BALANCE     PIC S9(9)V99 COMP-3.
       01 WS-ACCOUNT-STATUS      PIC X(1).
       01 WS-PENALTY-AMOUNT      PIC S9(7)V99 COMP-3 VALUE ZERO.
       01 WS-EOF-FLAG            PIC X(1) VALUE 'N'.
           88 END-OF-FILE        VALUE 'Y'.
           88 NOT-END-OF-FILE    VALUE 'N'.
       01 WS-PROCESSED-COUNT      PIC 9(5) VALUE ZERO.

       PROCEDURE DIVISION.
       MAIN-PROCESSING.
           DISPLAY 'Starting Customer Account Processing'
           OPEN INPUT CUSTOMER-FILE

           PERFORM UNTIL END-OF-FILE
               READ CUSTOMER-FILE
                   AT END SET END-OF-FILE TO TRUE
                   NOT AT END
                       MOVE CUSTOMER-ID TO WS-CUSTOMER-ID
                       MOVE CUSTOMER-NAME TO WS-CUSTOMER-NAME
                       MOVE ACCOUNT-BALANCE TO WS-ACCOUNT-BALANCE
                       MOVE ACCOUNT-STATUS TO WS-ACCOUNT-STATUS

                       PERFORM VALIDATE-ACCOUNT

                       IF WS-ACCOUNT-BALANCE < 0
                           PERFORM APPLY-PENALTY
                       END-IF

                       PERFORM UPDATE-ACCOUNT-BALANCE

                       ADD 1 TO WS-PROCESSED-COUNT
               END-READ
           END-PERFORM

           CLOSE CUSTOMER-FILE
           DISPLAY 'Processed ' WS-PROCESSED-COUNT ' accounts'
           STOP RUN.

       VALIDATE-ACCOUNT.
           IF WS-ACCOUNT-STATUS = 'A'
               CONTINUE
           ELSE
               IF WS-ACCOUNT-STATUS = 'I'
                   DISPLAY 'Account ' WS-CUSTOMER-ID ' is inactive'
               ELSE
                   DISPLAY 'Invalid status for account ' WS-CUSTOMER-ID
               END-IF
           END-IF.

       APPLY-PENALTY.
           CALL 'CALCULATE-PENALTY' USING WS-ACCOUNT-BALANCE
               WS-PENALTY-AMOUNT

           IF WS-PENALTY-AMOUNT > 0
               COMPUTE WS-ACCOUNT-BALANCE =
                   WS-ACCOUNT-BALANCE - WS-PENALTY-AMOUNT
               DISPLAY 'Applied penalty of ' WS-PENALTY-AMOUNT
                   ' to account ' WS-CUSTOMER-ID
           END-IF.

       UPDATE-ACCOUNT-BALANCE.
           IF WS-ACCOUNT-BALANCE < -10000
               MOVE 'S' TO WS-ACCOUNT-STATUS
               DISPLAY 'Account ' WS-CUSTOMER-ID ' suspended'
           ELSE
               IF WS-ACCOUNT-BALANCE >= 0
                   MOVE 'A' TO WS-ACCOUNT-STATUS
               END-IF
           END-IF.
