# UI Design Prompt: COBOL Legacy Modernization Platform (Concise Version)

## Project Overview

Design a **legacy system modernization platform** for COBOL programs. Users upload COBOL files, visualize program analysis through graphs (AST, CFG, DFG, PDG), and generate outputs (documentation, user stories, Java/Python code).

**Theme**: Spatial + Dark theme (VS Code/GitHub dark mode aesthetic)

---

## Three-Panel Layout

### **Left Panel (25%)**: COBOL Source Code
- Syntax-highlighted code editor
- Line numbers, collapsible sections
- File upload (drag-drop)

### **Center Panel (50%)**: Analysis Pipeline & Visualizations

**Pipeline Progress Bar** (top):
```
Upload → Parse → AST → CFG → DFG → PDG
```
Each step shows: ✅ Complete | ⏳ Processing | ❌ Error | ⏸️ Not Started

**Tabbed Graph Visualizations**:

**Tab 1: AST (Abstract Syntax Tree)**
- Hierarchical tree view (collapsible)
- Color-coded by node type (Program→Divisions→Sections→Statements)
- Click node → highlight code in left panel
- Search/filter nodes

**Tab 2: CFG (Control Flow Graph)**
- Flowchart with nodes (Entry, Basic Blocks, Control Nodes, Exit)
- Edges: Sequential (solid), TRUE/FALSE branches (dashed), Loops (curved)
- Color: Entry=green, Exit=red, Blocks=blue, Control=orange
- Interactive: Click node → see statements, highlight paths

**Tab 3: DFG (Data Flow Graph)**
- Data flow diagram showing variable dependencies
- Nodes = statements, Edges = data flow (labeled with variable names)
- Color: Definitions=blue, Uses=green
- Filter by variable, highlight flow paths

**Tab 4: PDG (Program Dependency Graph)**
- Combined control + data dependencies
- Control edges: dotted gray
- Data edges: solid colored (by variable)
- Features: Toggle dependency types, program slicing, impact analysis

### **Right Panel (25%)**: Output Generation

**Action Buttons**:
- 📄 Generate Documentation
- 📋 Generate User Story
- ☕ Convert to Java
- 🐍 Convert to Python
- 📊 Modernization Strategy
- 🔍 Extract Business Rules

**Output Display** (tabbed):
- Documentation: Technical docs with sections
- User Story: "As a [user], I want [goal] so that [benefit]" format
- Java/Python: Side-by-side comparison (COBOL | Target Language)
- Download options (PDF, Markdown, source files)

---

## Visual Design

**Colors** (Dark Theme):
- Background: #1a1a1a or #0d0d0d
- Panels: #2d2d2d
- Text: #e0e0e0 (body), #ffffff (headings)
- Accents: Blue (#4a9eff), Green (#4caf50), Orange (#ff9800), Red (#f44336)

**Graph Colors**:
- AST: Blue→Purple→Green→Yellow gradient
- CFG: Entry=green, Exit=red, Blocks=blue, Control=orange
- DFG: Definitions=blue, Uses=green, Variables=cyan
- PDG: Control=dotted gray, Data=variable-colored

**Typography**: Sans-serif headings, monospace code

---

## Key Interactions

- **Cross-panel sync**: Click graph node → highlight code | Click code → highlight graph nodes
- **Graph controls**: Zoom, pan, fit-to-view, filter, export PNG/SVG
- **Pipeline**: Step-by-step execution, skip steps, re-run analysis

---

## User Flows

1. **Upload & Analyze**: Upload COBOL → Auto-parse → View AST → Navigate to CFG/DFG/PDG
2. **Generate User Story**: Analyze graphs → Click button → View generated story → Download
3. **Convert to Java**: Review code → Click convert → View side-by-side → Download code
4. **Extract Rules**: Select code/graph → Extract → View business rules list

---

## Technical Requirements

- Support large graphs (1000+ nodes) with performance optimization
- Interactive graph rendering (D3.js, Cytoscape.js, or vis.js)
- Syntax highlighting for COBOL and generated code
- Responsive: Desktop (3-panel) → Tablet (collapsible) → Mobile (stacked)

---

## Success Criteria

Users should be able to:
✅ Understand COBOL structure through visualizations
✅ Navigate seamlessly between code and graphs
✅ Generate outputs with one click
✅ Work efficiently with large programs
✅ Export and share results

---

**Design Focus**: Clean, professional, enterprise-grade UI that makes complex COBOL analysis accessible and actionable.

