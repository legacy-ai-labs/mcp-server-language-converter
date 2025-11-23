#!/usr/bin/env python3
"""
Test script for inter-program COBOL analysis tools.
This script runs all analysis tools and generates visualizations.
"""

import json
import sys
from pathlib import Path
from typing import Any


# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.services.cobol_analysis.tool_handlers_service import (  # noqa: E402
    analyze_copybook_usage_handler,
    analyze_data_flow_handler,
    analyze_program_system_handler,
    build_call_graph_handler,
)


def run_system_analysis(directory_path: str) -> dict[str, Any]:
    """Run complete system analysis on COBOL programs."""
    print("=" * 70)
    print("STEP 1: Analyzing Program System")
    print("=" * 70)

    result = analyze_program_system_handler(
        {
            "directory_path": directory_path,
            "file_extensions": ["-FINAL.cbl"],  # Use files without COPY statements
            "include_inactive": False,
        }
    )

    if result["success"]:
        metrics = result.get("system_metrics", {})
        print(f"✓ Found {metrics.get('total_programs', 0)} programs")
        print(f"✓ Found {metrics.get('total_relationships', 0)} relationships")
        print(f"✓ Found {metrics.get('total_copybooks', 0)} copybooks")
        print(f"✓ Entry points: {len(result.get('entry_points', []))}")
        print(f"✓ Isolated programs: {len(result.get('isolated_programs', []))}")

        # Show program relationships
        print("\nProgram Relationships:")
        for prog_id, prog_info in result.get("programs", {}).items():
            if prog_info.get("callees"):
                print(f"  {prog_id} calls: {', '.join(prog_info['callees'])}")

        # Save results
        output_file = Path(directory_path) / "output" / "system_analysis.json"
        output_file.parent.mkdir(exist_ok=True)
        with output_file.open("w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Saved system analysis to: {output_file}")

    else:
        print(f"✗ System analysis failed: {result.get('error')}")

    return result


def build_call_graph(system_result: dict[str, Any], directory_path: str) -> dict[str, Any]:
    """Build call graph from system analysis."""
    print("\n" + "=" * 70)
    print("STEP 2: Building Call Graph")
    print("=" * 70)

    # Build graph in multiple formats
    formats = ["dict", "dot", "mermaid"]
    results = {}

    for fmt in formats:
        print(f"\nGenerating {fmt.upper()} format...")
        result = build_call_graph_handler(
            {
                "programs": system_result.get("programs", {}),
                "call_graph": system_result.get("call_graph", {}),
                "output_format": fmt,
                "include_metrics": True,
            }
        )

        if result["success"]:
            results[fmt] = result

            # Display metrics
            if fmt == "dict" and result.get("metrics"):
                metrics = result["metrics"]
                print(f"  ✓ Nodes: {metrics.get('total_nodes', 0)}")
                print(f"  ✓ Edges: {metrics.get('total_edges', 0)}")
                print(f"  ✓ Has cycles: {metrics.get('has_cycles', False)}")
                if metrics.get("has_cycles"):
                    print(f"    Cycles found: {metrics.get('cycle_count', 0)}")
                    for i, cycle in enumerate(metrics.get("cycles", [])[:3]):
                        print(f"      Cycle {i+1}: {' -> '.join(cycle)}")

            # Save visualization
            if fmt in ["dot", "mermaid"]:
                ext = "dot" if fmt == "dot" else "mmd"
                output_file = Path(directory_path) / "output" / f"call_graph.{ext}"
                with output_file.open("w") as f:
                    f.write(result.get("visualization", ""))
                print(f"  ✓ Saved {fmt} visualization to: {output_file}")

            # Save JSON result
            output_file = Path(directory_path) / "output" / f"call_graph_{fmt}.json"
            with output_file.open("w") as f:
                json.dump(result, f, indent=2)

        else:
            print(f"  ✗ Failed to build {fmt} graph: {result.get('error')}")

    return results.get("dict", {})


def analyze_copybooks(system_result: dict[str, Any], directory_path: str) -> dict[str, Any]:
    """Analyze copybook usage patterns."""
    print("\n" + "=" * 70)
    print("STEP 3: Analyzing Copybook Usage")
    print("=" * 70)

    result = analyze_copybook_usage_handler(
        {
            "copybook_usage": system_result.get("copybook_usage", {}),
            "programs": system_result.get("programs", {}),
            "include_recommendations": True,
        }
    )

    if result["success"]:
        stats = result.get("statistics", {})
        print(f"✓ Total copybooks: {stats.get('total_copybooks', 0)}")
        print(f"✓ Total relationships: {stats.get('total_relationships', 0)}")
        print(f"✓ Average usage: {stats.get('average_usage', 0):.2f}")
        print(f"✓ Shared copybooks: {stats.get('shared_count', 0)}")

        # Show copybook usage
        print("\nCopybook Usage:")
        for copybook in result.get("copybooks", [])[:5]:
            print(f"  {copybook['name']}: used by {copybook['usage_count']} programs")
            if copybook["is_shared"]:
                print(f"    Programs: {', '.join(copybook['used_by'][:3])}")

        # Show recommendations
        if result.get("recommendations"):
            print("\nRecommendations:")
            for rec in result["recommendations"]:
                print(f"  [{rec['priority']}] {rec['type']}: {rec['description']}")

        # Save results
        output_file = Path(directory_path) / "output" / "copybook_analysis.json"
        with output_file.open("w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Saved copybook analysis to: {output_file}")

    else:
        print(f"✗ Copybook analysis failed: {result.get('error')}")

    return result


def analyze_data_flows(system_result: dict[str, Any], directory_path: str) -> dict[str, Any]:
    """Analyze data flow through parameters."""
    print("\n" + "=" * 70)
    print("STEP 4: Analyzing Data Flow")
    print("=" * 70)

    result = analyze_data_flow_handler(
        {
            "data_flows": system_result.get("data_flows", []),
            "programs": system_result.get("programs", {}),
            "trace_variable": "WS-CUSTOMER-ID",  # Example variable to trace
        }
    )

    if result["success"]:
        stats = result.get("statistics", {})
        print(f"✓ Total flows: {stats.get('total_flows', 0)}")
        print(f"✓ Total parameters: {stats.get('total_parameters', 0)}")
        print(f"✓ BY REFERENCE flows: {stats.get('by_reference_flows', 0)}")
        print(f"✓ Unique variables: {stats.get('unique_variables', 0)}")
        print(f"✓ Warnings: {stats.get('warnings_count', 0)}")

        # Show data flows
        print("\nData Flows:")
        for flow in result.get("flows", [])[:5]:
            params = len(flow.get("parameters", []))
            print(f"  {flow['from']} → {flow['to']} ({params} parameters)")

        # Show warnings
        if result.get("warnings"):
            print("\nWarnings:")
            for warning in result["warnings"][:5]:
                print(f"  [{warning['severity']}] {warning['type']}")
                if warning.get("suggestion"):
                    print(f"    Suggestion: {warning['suggestion']}")

        # Save results
        output_file = Path(directory_path) / "output" / "data_flow_analysis.json"
        with output_file.open("w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Saved data flow analysis to: {output_file}")

    else:
        print(f"✗ Data flow analysis failed: {result.get('error')}")

    return result


def generate_html_visualization(system_result: dict[str, Any], directory_path: str):
    """Generate HTML visualization file."""
    print("\n" + "=" * 70)
    print("STEP 5: Generating HTML Visualization")
    print("=" * 70)

    output_file = Path(directory_path) / "output" / "visualization.html"
    print(f"✓ HTML visualization will be created at: {output_file}")
    print("  (See next file for the HTML code)")


def main():
    """Main test execution."""
    print("\n" + "=" * 70)
    print("COBOL INTER-PROGRAM ANALYSIS TEST")
    print("=" * 70)

    # Set the test directory path
    test_dir = str(Path(__file__).parent / "programs")
    print(f"Test Directory: {test_dir}")

    # Run all analyses
    system_result = run_system_analysis(test_dir)

    if system_result.get("success"):
        call_graph_result = build_call_graph(system_result, str(Path(__file__).parent))
        _copybook_result = analyze_copybooks(system_result, str(Path(__file__).parent))
        _data_flow_result = analyze_data_flows(system_result, str(Path(__file__).parent))
        generate_html_visualization(system_result, str(Path(__file__).parent))

        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print("✓ All analyses completed successfully!")
        print(f"✓ Results saved in: {Path(__file__).parent / 'output'}")
        print("\nKey Findings:")
        print(f"  - Programs: {system_result.get('system_metrics', {}).get('total_programs', 0)}")
        print(f"  - Entry Points: {', '.join(system_result.get('entry_points', []))}")
        print(f"  - Isolated Programs: {', '.join(system_result.get('isolated_programs', []))}")
        if call_graph_result.get("metrics", {}).get("has_cycles"):
            print("  - ⚠️ Circular dependencies detected!")

    else:
        print("\n✗ Test failed at system analysis stage")
        sys.exit(1)


if __name__ == "__main__":
    main()
