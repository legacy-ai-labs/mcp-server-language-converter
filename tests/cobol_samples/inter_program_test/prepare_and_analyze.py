#!/usr/bin/env python3
"""
Prepare COBOL files and generate analysis data for visualization.
This script handles COPY statements and generates proper relationships.
"""

import json
import re
from pathlib import Path
from typing import Any, cast


def remove_copy_statements(content: str) -> str:
    """Remove or comment out COPY statements."""
    # Remove COPY statements entirely
    content = re.sub(r"^\s*COPY\s+[\w-]+\s*\.?\s*$", "", content, flags=re.MULTILINE)
    return content


def further_clean_cobol_files(input_dir: Path, output_suffix: str = "-FINAL") -> None:
    """Further clean COBOL files by removing COPY statements."""
    print(f"Further cleaning COBOL files in {input_dir}")

    for cobol_file in input_dir.glob("*-CLEAN.cbl"):
        content = cobol_file.read_text()

        # Remove COPY statements
        content = remove_copy_statements(content)

        # Save with new suffix
        output_file = cobol_file.parent / cobol_file.name.replace(
            "-CLEAN.cbl", f"{output_suffix}.cbl"
        )
        output_file.write_text(content)
        print(f"  Created: {output_file.name}")


def extract_program_relationships(programs_dir: Path) -> dict[str, Any]:  # noqa: PLR0912
    """Extract program relationships directly from COBOL source."""
    programs = {}
    call_graph = {}
    copybook_usage: dict[str, list[str]] = {}
    data_flows = []

    # Read all COBOL files
    for cobol_file in programs_dir.glob("*.cbl"):
        if "-CLEAN" in cobol_file.name or "-FINAL" in cobol_file.name:
            continue

        program_id = cobol_file.stem.replace("-", "_")
        content = cobol_file.read_text()

        # Extract CALL statements
        calls = set()
        call_pattern = r"CALL\s+['\"]([^'\"]+)['\"]"
        for match in re.finditer(call_pattern, content):
            called_program = match.group(1).replace("-", "_")
            calls.add(called_program)

        # Extract COPY statements
        copies = set()
        copy_pattern = r"COPY\s+([A-Z0-9-]+)"
        for match in re.finditer(copy_pattern, content):
            copybook = match.group(1)
            copies.add(copybook)
            if copybook not in copybook_usage:
                copybook_usage[copybook] = []
            copybook_usage[copybook].append(program_id)

        # Extract parameters from CALL statements (simplified)
        for match in re.finditer(r"CALL\s+['\"]([^'\"]+)['\"]([^.]*)\.", content, re.DOTALL):
            called_program = match.group(1).replace("-", "_")
            call_context = match.group(2)

            # Look for USING clause
            if "USING" in call_context:
                params = []
                # Extract parameter names (simplified)
                param_pattern = r"BY\s+(VALUE|REFERENCE|CONTENT)?\s*([A-Z0-9-]+)"
                for param_match in re.finditer(param_pattern, call_context):
                    mode = param_match.group(1) or "REFERENCE"
                    param_name = param_match.group(2)
                    params.append({"name": param_name, "mode": mode, "type": "UNKNOWN"})

                if params:
                    data_flows.append(
                        {"from": program_id, "to": called_program, "parameters": params}
                    )

        # Store program info
        programs[program_id] = {
            "file_path": str(cobol_file),
            "program_id": program_id,
            "type": "BATCH" if "BATCH" in program_id else "PROGRAM",
            "callees": list(calls),
            "callers": [],  # Will be filled later
            "copybooks": list(copies),
            "has_linkage": "LINKAGE SECTION" in content,
            "entry_point": "MAIN" in program_id or "BATCH" in program_id,
        }

        # Build call graph
        if calls:
            call_graph[program_id] = list(calls)

    # Fill in callers
    for caller, callees in call_graph.items():
        for callee in callees:
            if callee in programs:
                cast(list, programs[callee]["callers"]).append(caller)

    # Identify entry points and isolated programs
    entry_points = []
    isolated_programs = []

    for prog_id, prog_info in programs.items():
        if not prog_info["callers"]:
            if prog_info["callees"]:
                entry_points.append(prog_id)
            else:
                isolated_programs.append(prog_id)

    # Calculate metrics
    total_relationships = sum(len(callees) for callees in call_graph.values())

    return {
        "success": True,
        "programs": programs,
        "call_graph": call_graph,
        "copybook_usage": copybook_usage,
        "data_flows": data_flows,
        "entry_points": entry_points,
        "isolated_programs": isolated_programs,
        "system_metrics": {
            "total_programs": len(programs),
            "total_relationships": total_relationships,
            "total_copybooks": len(copybook_usage),
            "entry_point_count": len(entry_points),
            "isolated_count": len(isolated_programs),
        },
    }


def detect_cycles(call_graph: dict[str, list[str]]) -> dict[str, Any]:
    """Detect cycles in the call graph using Tarjan's algorithm."""
    # Build adjacency list
    graph = {node: set(callees) for node, callees in call_graph.items()}

    # Add nodes that are called but don't call anything
    all_called = set()
    for callees in call_graph.values():
        all_called.update(callees)
    for node in all_called:
        if node not in graph:
            graph[node] = set()

    # Tarjan's algorithm for finding strongly connected components
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = {}
    sccs = []

    def strongconnect(node):
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        on_stack[node] = True
        stack.append(node)

        for successor in graph.get(node, []):
            if successor not in index:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif on_stack.get(successor, False):
                lowlinks[node] = min(lowlinks[node], index[successor])

        if lowlinks[node] == index[node]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == node:
                    break
            sccs.append(scc)

    for node in graph:
        if node not in index:
            strongconnect(node)

    # Find cycles (SCCs with more than one node or self-loops)
    cycles = []
    for scc in sccs:
        if len(scc) > 1 or len(scc) == 1 and scc[0] in graph.get(scc[0], []):
            cycles.append(scc)

    return {
        "has_cycles": len(cycles) > 0,
        "cycle_count": len(cycles),
        "cycles": cycles[:10],  # Limit to first 10 cycles
        "total_nodes": len(graph),
        "total_edges": sum(len(callees) for callees in graph.values()),
    }


def generate_visualization_data(analysis_result: dict[str, Any]) -> dict[str, Any]:
    """Generate data specifically for the visualization."""
    programs = analysis_result["programs"]
    call_graph = analysis_result["call_graph"]

    # Create nodes
    nodes = []
    for prog_id, prog_info in programs.items():
        node = {
            "data": {
                "id": prog_id,
                "label": prog_id.replace("_", "-"),
                "type": "entry"
                if prog_id in analysis_result["entry_points"]
                else "isolated"
                if prog_id in analysis_result["isolated_programs"]
                else "normal",
                "copybooks": len(prog_info.get("copybooks", [])),
                "calls_out": len(prog_info.get("callees", [])),
                "calls_in": len(prog_info.get("callers", [])),
            }
        }
        nodes.append(node)

    # Create edges
    edges = []
    for caller, callees in call_graph.items():
        for callee in callees:
            edge = {"data": {"id": f"{caller}->{callee}", "source": caller, "target": callee}}
            edges.append(edge)

    # Detect cycles for visualization
    cycle_info = detect_cycles(call_graph)

    # Mark nodes that are in cycles
    if cycle_info["has_cycles"]:
        nodes_in_cycles = set()
        for cycle in cycle_info["cycles"]:
            nodes_in_cycles.update(cycle)

        for node in nodes:
            if node["data"]["id"] in nodes_in_cycles:
                node["data"]["in_cycle"] = True

    return {
        "elements": {"nodes": nodes, "edges": edges},
        "metrics": {
            "total_programs": analysis_result["system_metrics"]["total_programs"],
            "total_relationships": analysis_result["system_metrics"]["total_relationships"],
            "total_copybooks": analysis_result["system_metrics"]["total_copybooks"],
            "entry_points": len(analysis_result["entry_points"]),
            "isolated_programs": len(analysis_result["isolated_programs"]),
            "has_cycles": cycle_info["has_cycles"],
            "cycle_count": cycle_info["cycle_count"],
        },
    }


def main():
    """Main execution."""
    print("\n" + "=" * 70)
    print("COBOL ANALYSIS DATA GENERATOR")
    print("=" * 70)

    # Set paths
    test_dir = Path(__file__).parent
    programs_dir = test_dir / "programs"
    output_dir = test_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Step 1: Further clean COBOL files (remove COPY statements)
    print("\nStep 1: Further cleaning COBOL files...")
    further_clean_cobol_files(programs_dir)

    # Step 2: Extract relationships from original files
    print("\nStep 2: Extracting program relationships...")
    analysis_result = extract_program_relationships(programs_dir)

    print(f"  Found {analysis_result['system_metrics']['total_programs']} programs")
    print(f"  Found {analysis_result['system_metrics']['total_relationships']} relationships")
    print(f"  Entry points: {', '.join(analysis_result['entry_points'])}")

    # Step 3: Generate visualization data
    print("\nStep 3: Generating visualization data...")
    viz_data = generate_visualization_data(analysis_result)

    # Step 4: Save analysis results
    print("\nStep 4: Saving results...")

    # Save full analysis
    analysis_file = output_dir / "system_analysis.json"
    with analysis_file.open("w") as f:
        json.dump(analysis_result, f, indent=2)
    print(f"  Saved analysis to: {analysis_file}")

    # Save visualization data
    viz_file = output_dir / "visualization_data.json"
    with viz_file.open("w") as f:
        json.dump(viz_data, f, indent=2)
    print(f"  Saved visualization data to: {viz_file}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Programs analyzed: {viz_data['metrics']['total_programs']}")
    print(f"✓ Relationships found: {viz_data['metrics']['total_relationships']}")
    print(f"✓ Copybooks used: {viz_data['metrics']['total_copybooks']}")
    print(f"✓ Entry points: {viz_data['metrics']['entry_points']}")
    print(f"✓ Isolated programs: {viz_data['metrics']['isolated_programs']}")

    if viz_data["metrics"]["has_cycles"]:
        print(f"⚠️  Circular dependencies detected: {viz_data['metrics']['cycle_count']} cycles")
        # Show first cycle
        if analysis_result.get("call_graph"):
            cycle_info = detect_cycles(analysis_result["call_graph"])
            if cycle_info["cycles"]:
                print(f"   Example cycle: {' -> '.join(cycle_info['cycles'][0])}")

    print(f"\n✓ Data ready for visualization in: {output_dir}")


if __name__ == "__main__":
    main()
