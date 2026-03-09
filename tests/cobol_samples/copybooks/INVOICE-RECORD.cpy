     ******************************************************************
     * INVOICE-RECORD.cpy
     * Invoice record structure shared across invoice processing programs
     ******************************************************************
      01  INVOICE-RECORD.
          05  INV-ID                PIC X(10).
          05  INV-CUSTOMER-ID       PIC X(10).
          05  INV-AMOUNT            PIC S9(9)V99 COMP-3.
          05  INV-DUE-DATE          PIC X(8).
          05  INV-STATUS            PIC X(1).
              88  INV-PENDING       VALUE 'P'.
              88  INV-PAID          VALUE 'Y'.
              88  INV-OVERDUE       VALUE 'O'.
              88  INV-CANCELLED     VALUE 'C'.
          05  INV-DAYS-OVERDUE      PIC 9(4) VALUE ZERO.
          05  INV-PENALTY-AMOUNT    PIC S9(7)V99 COMP-3 VALUE ZERO.
