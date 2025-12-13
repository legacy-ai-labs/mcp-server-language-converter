#!/usr/bin/env python3
"""
ProLeap AST Export Script

This script builds ProLeap from source and uses it to export COBOL AST to JSON.
The AST (Abstract Syntax Tree) is the raw parse tree from ANTLR, before semantic analysis.

Requirements:
- Java 17+ installed and available in PATH
- Maven 3+ installed and available in PATH
- Git installed and available in PATH
- Internet connection (for initial clone and dependencies)

Usage:
    python scripts/proleap_ast_export.py <cobol_file>
    python scripts/proleap_ast_export.py tests/cobol_samples/inter_program_test/programs/CUSTOMER-MGMT.cbl
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


def create_java_exporter() -> Path:
    """Create a Java AST exporter that outputs the raw parse tree."""
    java_dir = LIB_DIR / "java"
    java_dir.mkdir(parents=True, exist_ok=True)

    java_file = java_dir / "SimpleAstExporter.java"

    # AST exporter that traverses the ANTLR parse tree
    java_code = """
import io.proleap.cobol.CobolLexer;
import io.proleap.cobol.CobolParser;
import io.proleap.cobol.CobolParser.*;
import io.proleap.cobol.asg.params.impl.CobolParserParamsImpl;
import io.proleap.cobol.preprocessor.CobolPreprocessor;
import io.proleap.cobol.preprocessor.impl.CobolPreprocessorImpl;

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;

import java.io.*;
import java.nio.file.*;
import java.util.*;

public class SimpleAstExporter {

    private static StringBuilder json = new StringBuilder();
    private static int indentLevel = 0;
    private static int nodeId = 0;
    private static int maxDepth = 50;  // Prevent infinite recursion

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: java SimpleAstExporter <cobol_file> [output_json] [copybook_dir]");
            System.exit(1);
        }

        String cobolFile = args[0];
        String outputFile = args.length > 1 ? args[1] : cobolFile + ".ast.json";
        String copybookDir = args.length > 2 ? args[2] : null;

        System.err.println("Parsing AST: " + cobolFile);
        if (copybookDir != null) {
            System.err.println("Copybook directory: " + copybookDir);
        }

        try {
            File inputFile = new File(cobolFile);

            // Setup parameters with copybook directories
            CobolParserParamsImpl params = new CobolParserParamsImpl();
            params.setFormat(CobolPreprocessor.CobolSourceFormatEnum.FIXED);

            List<File> copyDirs = new ArrayList<>();
            copyDirs.add(inputFile.getParentFile());
            if (copybookDir != null) {
                copyDirs.add(new File(copybookDir));
            }
            params.setCopyBookDirectories(copyDirs);

            List<String> copyExtensions = Arrays.asList("cpy", "CPY", "copy", "COPY", "cbl", "CBL");
            params.setCopyBookExtensions(copyExtensions);

            // Preprocess the COBOL file first (handles COPY statements)
            CobolPreprocessorImpl preprocessor = new CobolPreprocessorImpl();
            String preprocessedCode = preprocessor.process(inputFile, params);

            // Parse with ANTLR
            CharStream charStream = CharStreams.fromString(preprocessedCode);
            CobolLexer lexer = new CobolLexer(charStream);
            CommonTokenStream tokens = new CommonTokenStream(lexer);
            CobolParser parser = new CobolParser(tokens);

            // Get the AST root
            StartRuleContext ast = parser.startRule();

            // Build JSON
            startObject();
            addString("source_file", cobolFile);
            addString("type", "AST");
            addString("parser", "ProLeap/ANTLR4");
            addNumber("total_tokens", tokens.getTokens().size());

            // Export the AST
            addKey("ast");
            exportNode(ast, tokens, 0);

            endObject();

            // Write output
            String jsonStr = json.toString();
            Files.writeString(Path.of(outputFile), jsonStr);
            System.err.println("AST exported to: " + outputFile);
            System.out.println(jsonStr);

        } catch (Exception e) {
            System.err.println("ERROR: " + e.getMessage());
            e.printStackTrace(System.err);
            System.exit(1);
        }
    }

    private static void exportNode(ParseTree node, CommonTokenStream tokens, int depth) {
        if (node == null || depth > maxDepth) {
            json.append("null");
            return;
        }

        startObject();

        int currentId = nodeId++;
        addNumber("id", currentId);

        // Node type (rule name or token type)
        String nodeType = node.getClass().getSimpleName().replace("Context", "");
        addString("type", nodeType);

        // For terminal nodes (tokens), include the text
        if (node instanceof TerminalNode) {
            TerminalNode terminal = (TerminalNode) node;
            Token token = terminal.getSymbol();

            addString("text", token.getText());
            addNumber("line", token.getLine());
            addNumber("column", token.getCharPositionInLine());
            addNumber("token_type", token.getType());

            // Get token name from vocabulary
            String tokenName = CobolLexer.VOCABULARY.getSymbolicName(token.getType());
            if (tokenName != null) {
                addString("token_name", tokenName);
            }
        } else if (node instanceof ParserRuleContext) {
            ParserRuleContext ruleCtx = (ParserRuleContext) node;

            // Rule index
            addNumber("rule_index", ruleCtx.getRuleIndex());

            // Get rule name from parser
            String ruleName = CobolParser.ruleNames[ruleCtx.getRuleIndex()];
            addString("rule_name", ruleName);

            // Source interval
            if (ruleCtx.getStart() != null) {
                addNumber("start_line", ruleCtx.getStart().getLine());
                addNumber("start_column", ruleCtx.getStart().getCharPositionInLine());
            }
            if (ruleCtx.getStop() != null) {
                addNumber("end_line", ruleCtx.getStop().getLine());
                addNumber("end_column", ruleCtx.getStop().getCharPositionInLine());
            }

            // Children
            int childCount = node.getChildCount();
            if (childCount > 0) {
                addKey("children");
                startArray();
                for (int i = 0; i < childCount; i++) {
                    exportNode(node.getChild(i), tokens, depth + 1);
                }
                endArray();
            }
        }

        endObject();
    }

    // JSON building helpers
    private static boolean needsComma = false;

    private static void startObject() {
        if (needsComma) json.append(",");
        json.append("\\n").append(indent()).append("{");
        indentLevel++;
        needsComma = false;
    }

    private static void endObject() {
        indentLevel--;
        json.append("\\n").append(indent()).append("}");
        needsComma = true;
    }

    private static void startArray() {
        json.append("[");
        indentLevel++;
        needsComma = false;
    }

    private static void endArray() {
        indentLevel--;
        json.append("\\n").append(indent()).append("]");
        needsComma = true;
    }

    private static void addKey(String key) {
        if (needsComma) json.append(",");
        json.append("\\n").append(indent()).append("\\"").append(key).append("\\": ");
        needsComma = false;
    }

    private static void addString(String key, String value) {
        if (needsComma) json.append(",");
        json.append("\\n").append(indent()).append("\\"").append(key).append("\\": \\"").append(escape(value)).append("\\"");
        needsComma = true;
    }

    private static void addNumber(String key, int value) {
        if (needsComma) json.append(",");
        json.append("\\n").append(indent()).append("\\"").append(key).append("\\": ").append(value);
        needsComma = true;
    }

    private static String indent() {
        return "  ".repeat(indentLevel);
    }

    private static String escape(String s) {
        if (s == null) return "";
        return s.replace("\\\\", "\\\\\\\\")
                .replace("\\"", "\\\\\\"")
                .replace("\\n", "\\\\n")
                .replace("\\r", "\\\\r")
                .replace("\\t", "\\\\t");
    }
}
"""

    java_file.write_text(java_code)
    print(f"Created Java AST exporter: {java_file}")
    return java_file


def compile_java_exporter(classpath: str, java_file: Path) -> Path:
    """Compile the Java AST exporter."""
    class_dir = java_file.parent / "classes"
    class_dir.mkdir(parents=True, exist_ok=True)

    print("Compiling Java AST exporter...")

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


def run_ast_export(
    classpath: str,
    class_dir: Path,
    cobol_file: Path,
    output_file: Path,
    copybook_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the AST exporter on a COBOL file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting AST for: {cobol_file}")
    if copybook_dir:
        print(f"Copybook directory: {copybook_dir}")

    # Build full classpath
    full_classpath = f"{class_dir}:{classpath}"

    cmd = [
        "java",
        "-cp",
        full_classpath,
        "SimpleAstExporter",
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
        print("ERROR: AST export failed")
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


def analyze_ast(ast: dict[str, Any]) -> None:
    """Analyze and display AST structure."""
    print("\n" + "=" * 70)
    print("AST ANALYSIS")
    print("=" * 70)

    if not ast:
        print("No AST data to analyze")
        return

    print(f"\nSource file: {ast.get('source_file', 'Unknown')}")
    print(f"Parser: {ast.get('parser', 'Unknown')}")
    print(f"Total tokens: {ast.get('total_tokens', 0)}")

    # Analyze the AST structure
    ast_root = ast.get("ast", {})
    if ast_root:
        stats = analyze_node(ast_root)

        print("\nAST Statistics:")
        print(f"  Total nodes: {stats['total_nodes']}")
        print(f"  Max depth: {stats['max_depth']}")
        print(f"  Terminal nodes (tokens): {stats['terminal_nodes']}")
        print(f"  Rule nodes: {stats['rule_nodes']}")

        print("\nTop-level structure:")
        print_ast_summary(ast_root, max_depth=2)

        print("\nRule type distribution (top 20):")
        sorted_rules = sorted(stats["rule_counts"].items(), key=lambda x: -x[1])[:20]
        for rule, count in sorted_rules:
            print(f"  {rule}: {count}")

    print("\n" + "=" * 70)
    print("SUMMARY: What ProLeap AST Provides")
    print("=" * 70)
    print(
        """
  ✓ Complete parse tree    - Every grammar rule and token
  ✓ Source locations       - Line/column for each node
  ✓ Token information      - Token type, text, position
  ✓ Hierarchical structure - Parent-child relationships
  ✓ Rule names             - ANTLR grammar rule names

  AST vs ASG:
  - AST: Raw syntax tree (what you see is what was parsed)
  - ASG: Semantic graph (resolved references, types, symbol tables)

  Use AST for:
  - Syntax validation
  - Code formatting/pretty-printing
  - Basic transformations
  - Comparing parse structures
    """
    )


def analyze_node(node: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """Recursively analyze AST node and collect statistics."""
    stats: dict[str, Any] = {
        "total_nodes": 1,
        "max_depth": depth,
        "terminal_nodes": 0,
        "rule_nodes": 0,
        "rule_counts": {},
    }

    node_type = node.get("type", "")

    # Check if terminal or rule node
    if "token_type" in node:
        stats["terminal_nodes"] = 1
    else:
        stats["rule_nodes"] = 1
        rule_name = node.get("rule_name", node_type)
        stats["rule_counts"][rule_name] = 1

    # Process children
    children = node.get("children", [])
    for child in children:
        if isinstance(child, dict):
            child_stats = analyze_node(child, depth + 1)
            stats["total_nodes"] += child_stats["total_nodes"]
            stats["max_depth"] = max(stats["max_depth"], child_stats["max_depth"])
            stats["terminal_nodes"] += child_stats["terminal_nodes"]
            stats["rule_nodes"] += child_stats["rule_nodes"]

            # Merge rule counts
            for rule, count in child_stats["rule_counts"].items():
                stats["rule_counts"][rule] = stats["rule_counts"].get(rule, 0) + count

    return stats


def print_ast_summary(
    node: dict[str, Any], indent: str = "", max_depth: int = 3, current_depth: int = 0
) -> None:
    """Print a summary of the AST structure."""
    if current_depth > max_depth:
        return

    node_type = node.get("type", "Unknown")
    rule_name = node.get("rule_name", "")

    # For terminal nodes, show the text
    if "text" in node:
        text = node["text"]
        if len(text) > 30:
            text = text[:27] + "..."
        print(f'{indent}[{node_type}] "{text}"')
    else:
        child_count = len(node.get("children", []))
        if rule_name:
            print(f"{indent}{rule_name} ({child_count} children)")
        else:
            print(f"{indent}{node_type} ({child_count} children)")

        # Show children
        children = node.get("children", [])
        for child in children[:5]:  # Limit to first 5 children
            if isinstance(child, dict):
                print_ast_summary(child, indent + "  ", max_depth, current_depth + 1)

        if len(children) > 5:
            print(f"{indent}  ... and {len(children) - 5} more children")


def main() -> None:
    """Main entry point."""
    print("=" * 70)
    print("ProLeap COBOL Parser - AST Export Tool")
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

    # Create and compile Java exporter
    java_file = create_java_exporter()
    class_dir = compile_java_exporter(classpath, java_file)

    # Run AST export
    output_file = OUTPUT_DIR / f"{cobol_file.stem}.ast.json"
    ast = run_ast_export(classpath, class_dir, cobol_file, output_file, copybook_dir)

    # Analyze results
    analyze_ast(ast)

    if ast:
        print(f"\nFull AST saved to: {output_file}")


if __name__ == "__main__":
    main()
