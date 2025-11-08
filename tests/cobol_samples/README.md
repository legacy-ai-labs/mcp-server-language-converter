# COBOL Test Samples

This directory contains COBOL programs used for testing the reverse engineering system.

## Test Files

### 1. CUSTOMER-ACCOUNT-MAIN.cbl
**Main program** that processes customer account records.

**Features demonstrated:**
- File I/O (FD, SELECT, READ, OPEN, CLOSE)
- WORKING-STORAGE variable declarations
- PERFORM statements (internal procedures)
- CALL statements (external subprograms)
- IF/ELSE nested conditionals
- COMPUTE statements
- Data flow between procedures
- Loop processing (PERFORM UNTIL)

**Calls:**
- `CALCULATE-PENALTY` (external subprogram)
- Internal procedures: `VALIDATE-ACCOUNT`, `APPLY-PENALTY`, `UPDATE-ACCOUNT-BALANCE`

### 2. CALCULATE-PENALTY.cbl
**Subprogram** called by main program to calculate penalty amounts.

**Features demonstrated:**
- LINKAGE SECTION (parameter passing)
- PROCEDURE DIVISION USING (parameter interface)
- COMPUTE statements with calculations
- IF/ELSE conditionals
- EXIT PROGRAM
- Internal procedure: `VALIDATE-PENALTY-CALCULATION`

**Called by:** CUSTOMER-ACCOUNT-MAIN

### 3. ACCOUNT-VALIDATOR.cbl
**Subprogram** for account validation logic.

**Features demonstrated:**
- LINKAGE SECTION (multiple parameters)
- EVALUATE statement (switch-like logic)
- PERFORM statements
- 88-level condition names
- Multiple internal procedures: `CHECK-CUSTOMER-ID`, `CHECK-ACCOUNT-BALANCE`, `CHECK-ACCOUNT-STATUS`

**Called by:** Can be called from main program (not currently called in test files)

## COBOL Features Covered

- ✅ All four divisions (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)
- ✅ File definitions (FD, SELECT)
- ✅ WORKING-STORAGE SECTION
- ✅ LINKAGE SECTION
- ✅ PERFORM statements (internal procedures)
- ✅ CALL statements (external subprograms)
- ✅ IF/ELSE conditionals
- ✅ EVALUATE statements
- ✅ COMPUTE statements
- ✅ File I/O operations
- ✅ Data flow between procedures
- ✅ Variable declarations (PIC clauses, level numbers)
- ✅ 88-level condition names

## Usage

These files are used for:
1. Testing COBOL parser
2. Testing AST construction
3. Testing CFG construction (control flow)
4. Testing DFG construction (data flow)
5. Integration testing of full analysis pipeline
