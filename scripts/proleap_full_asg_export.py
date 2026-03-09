#!/usr/bin/env python3
"""
ProLeap Full ASG Export Script (DEPRECATED)

DEPRECATED: Use the ProLeap HTTP service instead:
    curl -X POST http://localhost:4567/v1/cobol/asg/text \
         -H 'Content-Type: application/json' \
         -d '{"code": "...", "format": "FIXED"}'

Or start the service via Docker:
    docker compose -f docker/docker-compose.yml up -d proleap-service

This script builds ProLeap from source and uses the FullAsgExporter to export
complete COBOL ASG to JSON, including all clause types and cross-references.

Requirements:
- Java 17+ installed and available in PATH
- Maven 3+ installed and available in PATH
- Git installed and available in PATH
- Internet connection (for initial clone and dependencies)

Usage:
    python scripts/proleap_full_asg_export.py <cobol_file>
    python scripts/proleap_full_asg_export.py tests/cobol_samples/inter_program_test/programs/CUSTOMER-MGMT.cbl
"""

import json
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any, cast


# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
LIB_DIR = PROJECT_ROOT / "lib"
JAVA_DIR = LIB_DIR / "java"
PROLEAP_DIR = LIB_DIR / "proleap-cobol-parser"
OUTPUT_DIR = PROJECT_ROOT / "output" / "proleap"


def check_prerequisites() -> bool:
    """Check if Java, Maven, and Git are available."""
    tools = ["java", "mvn", "git"]
    missing = []

    for tool in tools:
        try:
            subprocess.run(  # nosec B603, B607
                [tool, "--version"],
                capture_output=True,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing.append(tool)

    if missing:
        print(f"ERROR: Missing required tools: {', '.join(missing)}")
        print("Please install them and ensure they are in PATH.")
        return False

    # Check Java version
    result = subprocess.run(["java", "-version"], capture_output=True, text=True, check=False)  # nosec B603, B607
    version_output = result.stderr or result.stdout
    print(f"Java: {version_output.splitlines()[0]}")

    result = subprocess.run(["mvn", "--version"], capture_output=True, text=True, check=False)  # nosec B603, B607
    print(f"Maven: {result.stdout.splitlines()[0]}")

    return True


def clone_proleap() -> bool:
    """Clone ProLeap repository if not present."""
    LIB_DIR.mkdir(parents=True, exist_ok=True)

    if PROLEAP_DIR.exists():
        print(f"ProLeap already cloned: {PROLEAP_DIR}")
        return True

    print("Cloning ProLeap repository...")
    result = subprocess.run(  # nosec B603, B607
        ["git", "clone", "https://github.com/uwol/proleap-cobol-parser.git", str(PROLEAP_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"ERROR: Failed to clone repository: {result.stderr}")
        return False

    print(f"Cloned to: {PROLEAP_DIR}")
    return True


def build_proleap() -> bool:
    """Build ProLeap using Maven."""
    # Check if already built
    target_dir = PROLEAP_DIR / "target"
    if target_dir.exists():
        jars = list(target_dir.glob("proleap-cobol-parser-*.jar"))
        if jars and not any("sources" in str(j) or "javadoc" in str(j) for j in jars):
            print(f"ProLeap already built: {jars[0]}")
            return True

    print("Building ProLeap (this may take a few minutes)...")
    result = subprocess.run(  # nosec B603, B607
        ["mvn", "package", "-DskipTests", "-q"],
        cwd=PROLEAP_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print("ERROR: Maven build failed:")
        print(result.stderr)
        return False

    print("Build successful!")
    return True


def get_classpath() -> str:
    """Get the classpath including ProLeap and all dependencies."""
    target_dir = PROLEAP_DIR / "target"

    # Find the main JAR
    jars = [
        j
        for j in target_dir.glob("proleap-cobol-parser-*.jar")
        if "sources" not in str(j) and "javadoc" not in str(j)
    ]

    if not jars:
        raise FileNotFoundError("ProLeap JAR not found")

    main_jar = jars[0]

    # Get dependencies using Maven
    deps_file = target_dir / "classpath.txt"
    if not deps_file.exists():
        print("Resolving dependencies...")
        result = subprocess.run(  # nosec B603, B607
            ["mvn", "dependency:build-classpath", f"-Dmdep.outputFile={deps_file}", "-q"],
            cwd=PROLEAP_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(f"Warning: Could not resolve dependencies: {result.stderr}")
            return str(main_jar)

    deps_classpath = deps_file.read_text().strip() if deps_file.exists() else ""
    return f"{main_jar}:{deps_classpath}" if deps_classpath else str(main_jar)


def compile_full_asg_exporter(classpath: str) -> Path:
    """Compile the FullAsgExporter Java class."""
    java_file = JAVA_DIR / "FullAsgExporter.java"

    if not java_file.exists():
        raise FileNotFoundError(f"FullAsgExporter.java not found at {java_file}")

    class_dir = JAVA_DIR / "classes"
    class_dir.mkdir(parents=True, exist_ok=True)

    # Check if already compiled and up to date
    class_file = class_dir / "FullAsgExporter.class"
    if class_file.exists():
        java_mtime = java_file.stat().st_mtime
        class_mtime = class_file.stat().st_mtime
        if class_mtime > java_mtime:
            print(f"FullAsgExporter already compiled: {class_file}")
            return class_dir

    print("Compiling FullAsgExporter...")

    result = subprocess.run(  # nosec B603, B607
        [
            "javac",
            "-cp",
            classpath,
            "-d",
            str(class_dir),
            str(java_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print("ERROR: Compilation failed:")
        print(result.stderr)
        sys.exit(1)

    print(f"Compiled to: {class_dir}")
    return class_dir


def run_full_asg_export(
    classpath: str,
    class_dir: Path,
    cobol_file: Path,
    output_file: Path,
    copybook_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the FullAsgExporter on a COBOL file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting Full ASG for: {cobol_file}")
    if copybook_dir:
        print(f"Copybook directory: {copybook_dir}")

    # Build full classpath
    full_classpath = f"{class_dir}:{classpath}"

    cmd = [
        "java",
        "-cp",
        full_classpath,
        "FullAsgExporter",
        str(cobol_file),
        str(output_file),
    ]

    if copybook_dir:
        cmd.append(str(copybook_dir))

    result = subprocess.run(  # nosec B603
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    # Print stderr (status messages)
    if result.stderr:
        print(result.stderr.strip())

    if result.returncode != 0:
        print("ERROR: Full ASG export failed")
        return {}

    # Parse and return JSON
    try:
        with output_file.open() as f:
            return cast(dict[str, Any], json.load(f))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"ERROR: Failed to parse JSON output: {e}")
        if result.stdout:
            print(f"Raw output:\n{result.stdout[:2000]}")
        return {}


def _print_statement_detail(stmt: dict[str, Any]) -> None:
    """Print detailed info for a statement."""
    stmt_type = stmt.get("statement_type", "?")

    if stmt_type == "CALL":
        call_det = stmt.get("call_details", {})
        target = call_det.get("target_program", "?")
        using_params = call_det.get("using_phrase", {}).get("parameters", [])
        param_count = len(using_params)
        print(f"    CALL {target} ({param_count} params)")
    elif stmt_type == "PERFORM":
        perf_det = stmt.get("perform_details", {})
        perf_type = perf_det.get("perform_type", "SIMPLE")
        target = perf_det.get("target_paragraph", "")
        if target:
            print(f"    PERFORM {target} ({perf_type})")
        else:
            print(f"    PERFORM INLINE ({perf_type})")


def _analyze_data_division(dd: dict[str, Any]) -> None:
    """Analyze and print Data Division content."""
    # Working Storage
    ws = dd.get("working_storage", {})
    ws_entries = ws.get("entries", [])
    print(f"\nWorking-Storage Section ({len(ws_entries)} root entries):")
    print_data_hierarchy_full(ws_entries, "  ", max_depth=3)

    # Linkage Section
    ls = dd.get("linkage_section", {})
    ls_entries = ls.get("entries", [])
    if ls_entries:
        print(f"\nLinkage Section ({len(ls_entries)} entries):")
        print_data_hierarchy_full(ls_entries, "  ", max_depth=2)

    # File Section
    fs = dd.get("file_section", {})
    fd_entries = fs.get("file_descriptions", [])
    if fd_entries:
        print(f"\nFile Section ({len(fd_entries)} file descriptions):")
        for fd in fd_entries:
            print(f"  FD {fd.get('name', '?')}")
            records = fd.get("record_entries", [])
            if records:
                print(f"    Records: {len(records)}")


def _analyze_procedure_division(pd: dict[str, Any]) -> None:
    """Analyze and print Procedure Division content."""
    # USING/GIVING
    using = pd.get("using_clause", {})
    if using:
        params = using.get("parameter_names", [])
        print(f"\nProcedure Division USING: {', '.join(params)}")

    giving = pd.get("giving_clause", {})
    if giving:
        print(f"Procedure Division GIVING: {giving.get('giving_name', '?')}")

    # Sections
    sections = pd.get("sections", [])
    print(f"\nSections: {len(sections)}")
    for section in sections:
        para_count = len(section.get("paragraphs", []))
        print(f"  {section.get('name', '?')}: {para_count} paragraphs")

    # Paragraphs
    paragraphs = pd.get("paragraphs", [])
    print(f"\nRoot Paragraphs: {len(paragraphs)}")
    for para in paragraphs[:10]:  # Show first 10
        name = para.get("name", "?")
        stmt_count = para.get("statement_count", 0)
        print(f"  {name}: {stmt_count} statements")

        # Show statement details
        statements = para.get("statements", [])
        for stmt in statements[:5]:  # Show first 5 statements
            _print_statement_detail(stmt)

    # All paragraphs list
    all_paras = pd.get("all_paragraphs", [])
    print(f"\nAll Paragraphs: {len(all_paras)}")

    # CALL statements summary
    calls = pd.get("call_statements", [])
    print(f"\nCALL Statements Summary: {len(calls)}")
    for call in calls:
        para = call.get("paragraph", "?")
        target = call.get("target", "?")
        param_count = call.get("parameter_count", 0)
        print(f"  {para} -> CALL {target} ({param_count} params)")


def analyze_full_asg(asg: dict[str, Any]) -> None:
    """Analyze and display full ASG structure."""
    print("\n" + "=" * 70)
    print("FULL ASG ANALYSIS")
    print("=" * 70)

    if not asg:
        print("No ASG data to analyze")
        return

    print(f"\nSource file: {asg.get('source_file', 'Unknown')}")
    print(f"ProLeap version: {asg.get('proleap_version', 'Unknown')}")
    print(f"Export type: {asg.get('export_type', 'Unknown')}")

    for cu in asg.get("compilation_units", []):
        # Identification Division
        id_div = cu.get("identification_division", {})
        program_id = id_div.get("program_id", "UNKNOWN")

        print(f"\n{'=' * 50}")
        print(f"Program: {program_id}")
        if id_div.get("author"):
            print(f"Author: {id_div['author']}")
        print("=" * 50)

        # Data Division analysis
        dd = cu.get("data_division", {})
        _analyze_data_division(dd)

        # Procedure Division analysis
        pd = cu.get("procedure_division", {})
        _analyze_procedure_division(pd)

    print("\n" + "=" * 70)
    print("SUMMARY: What Full ProLeap ASG Provides")
    print("=" * 70)
    print(
        """
  ✓ Identification Division - Program ID, author, dates
  ✓ Data Division - All sections (Working-Storage, Linkage, File, Local)
  ✓ Full clause extraction:
      - PICTURE with string
      - USAGE type
      - VALUE clause with literals
      - OCCURS with DEPENDING ON, INDEXED BY, KEY IS
      - REDEFINES with target reference
      - SYNCHRONIZED, SIGN, EXTERNAL, GLOBAL
      - JUSTIFIED, BLANK WHEN ZERO
      - Level 88 conditions with values
      - Level 66 RENAMES with from/to
  ✓ Cross-references (getCalls()) - Who references each data item
  ✓ Procedure Division - USING/GIVING clauses
  ✓ Sections and Paragraphs with statement details
  ✓ CALL statements - Target, USING params, GIVING, exception handling
  ✓ PERFORM statements - Type (TIMES/UNTIL/VARYING), targets
    """
    )


def _build_clauses_summary(entry: dict[str, Any]) -> list[str]:
    """Build a list of clause strings for a data entry."""
    clauses = []
    if entry.get("picture"):
        pic = entry["picture"].get("picture_string", "?")
        clauses.append(f"PIC {pic}")
    if entry.get("usage"):
        clauses.append(entry["usage"])
    if entry.get("occurs"):
        occ = entry["occurs"]
        if occ.get("from_value") and occ.get("to_value"):
            clauses.append(f"OCCURS {occ['from_value']} TO {occ['to_value']}")
        elif occ.get("from_value"):
            clauses.append(f"OCCURS {occ['from_value']}")
        if occ.get("depending_on_name"):
            clauses.append(f"DEPENDING ON {occ['depending_on_name']}")
    if entry.get("redefines"):
        red = entry["redefines"]
        clauses.append(f"REDEFINES {red.get('redefines_name', '?')}")
    if entry.get("is_external"):
        clauses.append("EXTERNAL")
    if entry.get("is_global"):
        clauses.append("GLOBAL")
    if entry.get("value"):
        val = entry["value"].get("value", "?")
        clauses.append(f"VALUE {val}")
    return clauses


def _print_data_entry(entry: dict[str, Any], indent: str) -> None:
    """Print a single data entry with clause details."""
    level = entry.get("level", "?")
    name = entry.get("name", "?")
    entry_type = entry.get("entry_type", "?")
    is_filler = entry.get("is_filler", False)

    # Build type indicator
    type_indicator = f"[{entry_type[0]}]" if entry_type else "[?]"

    # Build clause summary
    clauses = _build_clauses_summary(entry)
    clause_str = f" ({', '.join(clauses)})" if clauses else ""

    # Print entry
    name_display = "FILLER" if is_filler else name
    print(f"{indent}{level:02d} {name_display} {type_indicator}{clause_str}")

    # Show calls (cross-references)
    calls = entry.get("calls", [])
    if calls:
        print(f"{indent}   Referenced by: {len(calls)} call(s)")

    # Print condition values for level 88
    cond_values = entry.get("condition_values", [])
    for cv in cond_values[:3]:  # Show first 3
        from_val = cv.get("from", "?")
        to_val = cv.get("to")
        if to_val:
            print(f"{indent}   VALUE {from_val} THRU {to_val}")
        else:
            print(f"{indent}   VALUE {from_val}")


def print_data_hierarchy_full(
    entries: list[dict[str, Any]], indent: str, max_depth: int = 5, current_depth: int = 0
) -> None:
    """Print data hierarchy with clause details."""
    if current_depth >= max_depth:
        if entries:
            print(f"{indent}... ({len(entries)} more entries)")
        return

    for entry in entries:
        _print_data_entry(entry, indent)

        # Print children recursively
        children = entry.get("children", [])
        if children:
            print_data_hierarchy_full(children, indent + "  ", max_depth, current_depth + 1)


def main() -> None:
    """Main entry point."""
    print("=" * 70)
    print("ProLeap COBOL Parser - Full ASG Export Tool")
    print("=" * 70)

    # Check arguments
    if len(sys.argv) < 2:
        print(f"\nUsage: python {sys.argv[0]} <cobol_file>")
        print("\nExample:")
        print(
            f"  python {sys.argv[0]} tests/cobol_samples/inter_program_test/programs/CUSTOMER-MGMT.cbl"
        )
        sys.exit(1)

    cobol_file = Path(sys.argv[1]).resolve()
    if not cobol_file.exists():
        print(f"ERROR: File not found: {cobol_file}")
        sys.exit(1)

    # Try to auto-detect copybook directory
    copybook_dir = None
    parent_dir = cobol_file.parent
    possible_dirs = [
        parent_dir.parent / "copybooks",
        parent_dir / "copybooks",
        parent_dir.parent / "copy",
        parent_dir / "copy",
    ]
    for d in possible_dirs:
        if d.exists() and d.is_dir():
            copybook_dir = d
            break

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Clone and build ProLeap
    if not clone_proleap():
        sys.exit(1)

    if not build_proleap():
        sys.exit(1)

    # Get classpath
    try:
        classpath = get_classpath()
        print(f"\nClasspath ready ({len(classpath)} chars)")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Compile FullAsgExporter
    try:
        class_dir = compile_full_asg_exporter(classpath)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Run Full ASG export
    output_file = OUTPUT_DIR / f"{cobol_file.stem}.full-asg.json"
    asg = run_full_asg_export(classpath, class_dir, cobol_file, output_file, copybook_dir)

    # Analyze results
    analyze_full_asg(asg)

    if asg:
        print(f"\nFull ASG saved to: {output_file}")


if __name__ == "__main__":
    main()
