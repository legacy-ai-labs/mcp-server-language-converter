# UI Design Prompt: COBOL Legacy Modernization Platform

## Project Overview

Design a **legacy system modernization platform** focused on COBOL program analysis and migration. The platform allows users to upload COBOL files, visualize program structure through multiple graph types (AST, CFG, DFG, PDG), and generate outputs like documentation, user stories, and modern language code (Java, Python).

**Theme**: Spatial + Dark theme with modern, professional aesthetics suitable for enterprise software.

---

## Core Workflow Pipeline

The platform follows a **sequential analysis pipeline**:

```
COBOL Source Code → Parse → AST → CFG → DFG → PDG → Outputs
```

Each step builds upon the previous one:
- **AST** (Abstract Syntax Tree): Syntactic structure
- **CFG** (Control Flow Graph): Execution paths and branches
- **DFG** (Data Flow Graph): Variable dependencies and data transformations
- **PDG** (Program Dependency Graph): Combined control + data dependencies

---

## Layout Structure: Three-Panel Design

### **Left Panel: Source Code Viewer** (25% width)
- **COBOL source code display** with syntax highlighting
- Line numbers
- Collapsible sections (IDENTIFICATION, DATA, PROCEDURE divisions)
- Search/filter functionality
- File upload area (drag-and-drop or browse)
- File list sidebar (if multiple files uploaded)

### **Center Panel: Analysis Pipeline & Visualizations** (50% width)

#### **Pipeline Progress Indicator** (Top)
Visual pipeline showing:
- Upload → Parse → AST → CFG → DFG → PDG
- Each step shows: ✅ Complete, ⏳ Processing, ❌ Error, ⏸️ Not Started
- Clickable steps to jump to specific visualizations
- Progress percentage for current step

#### **Graph Visualization Area** (Main Content)
**Tabbed Interface** (recommended) or **Accordion** for each graph type:

**Tab 1: AST (Abstract Syntax Tree)**
- **Tree visualization** (hierarchical, collapsible)
- Node types: Program → Divisions → Sections → Paragraphs → Statements
- Color coding:
  - Program node: Dark blue
  - Divisions: Purple shades
  - Procedures: Green shades
  - Statements: Yellow/Orange shades
- Click node to highlight corresponding code in left panel
- Search/filter nodes
- Expand/collapse branches
- Show node details on hover (statement type, line number, variable names)

**Tab 2: CFG (Control Flow Graph)**
- **Flowchart/digraph visualization** (nodes and edges)
- Node types:
  - Entry node (green, rounded)
  - Basic blocks (rectangles, show statement count)
  - Control nodes (diamonds for IF, rounded rectangles for PERFORM)
  - Exit node (red, rounded)
- Edge types with different styles:
  - Sequential: Solid gray arrow
  - TRUE branch: Green dashed arrow
  - FALSE branch: Red dashed arrow
  - LOOP: Curved arrow with loop indicator
- Interactive features:
  - Click node to see statements in popup
  - Highlight execution path on hover
  - Zoom/pan controls
  - Filter by edge type
  - Show/hide node labels

**Tab 3: DFG (Data Flow Graph)**
- **Data flow diagram** showing variable dependencies
- Nodes represent statements that define/use variables
- Edges show data flow (arrow from definition to use)
- Edge labels show variable names
- Color coding:
  - Definition nodes: Blue
  - Use nodes: Green
  - Variables: Shown in edge labels
- Interactive features:
  - Click variable name to highlight all related nodes
  - Filter by variable name
  - Show variable definition chain
  - Highlight data flow path for selected variable

**Tab 4: PDG (Program Dependency Graph)**
- **Combined dependency graph** (control + data)
- Two edge types visually distinct:
  - Control dependencies: Dotted lines (gray)
  - Data dependencies: Solid lines (colored by variable)
- Node grouping by feature/functionality
- Interactive features:
  - Toggle control vs data dependencies
  - Filter by dependency type
  - Highlight impact of selected node (what it affects)
  - Program slicing: Select variable → show all affecting code

**Alternative Layout Option**: **Accordion** instead of tabs
- Each graph type in collapsible section
- All graphs visible simultaneously (scrolling)
- Better for comparing graphs side-by-side

### **Right Panel: Output Generation** (25% width)

#### **Output Options Section** (Top)
Action buttons for generating outputs:
- 📄 **Generate Documentation** (technical documentation)
- 📋 **Generate User Story** (business user story)
- ☕ **Convert to Java** (code migration)
- 🐍 **Convert to Python** (code migration)
- 📊 **Modernization Strategy** (migration recommendations)
- 🔍 **Extract Business Rules** (business logic extraction)

#### **Output Display Area** (Main Content)
- Tabbed interface for different output types
- Each output shows:
  - Generated content (formatted, syntax-highlighted for code)
  - Download button (PDF, Markdown, or source file)
  - Copy to clipboard
  - Regenerate button
- **Documentation Tab**: Technical docs with sections for:
  - Program overview
  - Data structures
  - Procedure descriptions
  - Control flow summary
- **User Story Tab**: Business-focused user stories in format:
  - "As a [user type], I want [goal] so that [benefit]"
  - Acceptance criteria
  - Related code sections
- **Java/Python Tab**: Converted code with:
  - Side-by-side comparison (COBOL vs Java/Python)
  - Syntax highlighting
  - Comments explaining conversions
  - Warnings/notes about complex conversions

---

## Visual Design Specifications

### **Color Palette** (Dark Theme)
- **Background**: Deep dark gray (#1a1a1a) or black (#0d0d0d)
- **Panels**: Slightly lighter (#2d2d2d) with subtle borders
- **Text**: Light gray (#e0e0e0) for body, white (#ffffff) for headings
- **Accents**:
  - Primary: Blue (#4a9eff) for actions
  - Success: Green (#4caf50) for completed steps
  - Warning: Orange (#ff9800) for warnings
  - Error: Red (#f44336) for errors
  - Info: Cyan (#00bcd4) for information

### **Graph Visualization Colors**
- **AST**: Hierarchical color gradient (blue → purple → green → yellow)
- **CFG**: 
  - Entry: Green (#4caf50)
  - Exit: Red (#f44336)
  - Basic blocks: Blue (#2196f3)
  - Control nodes: Orange (#ff9800)
- **DFG**: 
  - Definitions: Blue (#2196f3)
  - Uses: Green (#4caf50)
  - Variables: Cyan (#00bcd4)
- **PDG**: 
  - Control edges: Gray dotted
  - Data edges: Variable-colored solid lines

### **Typography**
- **Headings**: Sans-serif, bold (e.g., Inter, Roboto)
- **Code**: Monospace (e.g., JetBrains Mono, Fira Code)
- **Body**: Sans-serif, regular weight

### **Spacing & Layout**
- Generous whitespace between panels
- Consistent padding (16px, 24px, 32px scale)
- Rounded corners (8px) for panels and buttons
- Subtle shadows for depth

---

## Interactive Features

### **Cross-Panel Synchronization**
- Click node in graph → highlight code in left panel
- Click code line → highlight related nodes in graphs
- Hover over graph node → show tooltip with details
- Select variable → highlight across all visualizations

### **Graph Controls**
- **Zoom**: Mouse wheel or +/- buttons
- **Pan**: Click and drag
- **Fit to view**: Auto-layout button
- **Filter**: Search bar for nodes/variables
- **Export**: Download graph as PNG/SVG
- **Fullscreen**: Expand graph to full view

### **Pipeline Controls**
- **Step-by-step execution**: Run pipeline step by step
- **Skip steps**: Jump to specific analysis level
- **Re-run**: Regenerate specific graph
- **Compare**: Compare graphs from different COBOL files

---

## Key User Flows

### **Flow 1: Upload & Analyze**
1. User uploads COBOL file (drag-drop or browse)
2. File appears in left panel with syntax highlighting
3. Pipeline automatically starts: Parse → AST
4. AST tab becomes active, tree visualization appears
5. User can click through tabs to see CFG, DFG, PDG
6. Each graph loads progressively (shows loading state)

### **Flow 2: Generate User Story**
1. User analyzes graphs (especially PDG for feature boundaries)
2. Clicks "Generate User Story" button in right panel
3. System processes AST + CFG + DFG + PDG
4. User Story appears in right panel output area
5. User can download as Markdown or PDF

### **Flow 3: Convert to Java**
1. User reviews COBOL code and graphs
2. Clicks "Convert to Java" button
3. System uses AST to generate Java code
4. Side-by-side comparison appears (COBOL | Java)
5. User can download Java file or copy code

### **Flow 4: Extract Business Rules**
1. User selects specific section in code or graph
2. Clicks "Extract Business Rules"
3. System analyzes selected code + dependencies
4. Business rules list appears with:
   - Rule description
   - Related code sections
   - Dependencies
   - Impact analysis

---

## Responsive Considerations

- **Desktop**: Full three-panel layout
- **Tablet**: Collapsible side panels, center panel full-width
- **Mobile**: Stack panels vertically, graphs scrollable

---

## Additional UI Elements

### **Header/Navigation**
- Logo/branding
- File management (open, save, new)
- Settings (theme, graph preferences)
- Help/documentation link

### **Status Bar** (Bottom)
- Current file name
- Analysis status
- Graph statistics (node count, edge count)
- Processing time

### **Tooltips & Help**
- Contextual help for each graph type
- Tooltips explaining graph elements
- Keyboard shortcuts indicator
- Tutorial/onboarding for first-time users

---

## Technical Considerations for Design

### **Graph Rendering**
- Use libraries like D3.js, Cytoscape.js, or vis.js for interactive graphs
- AST: Tree layout algorithm
- CFG/DFG/PDG: Force-directed or hierarchical layout
- Support for large graphs (1000+ nodes) with performance optimization

### **Code Editor**
- Syntax highlighting for COBOL
- Line numbers
- Code folding (collapse divisions/sections)
- Search and replace

### **Output Formatting**
- Markdown rendering for documentation
- Syntax highlighting for generated code
- PDF generation for documentation/user stories

---

## Inspiration Notes

- **Spatial theme**: Think VS Code dark theme, GitHub dark mode
- **Graph visualizations**: Similar to code analysis tools (Sourcegraph, CodeQL)
- **Pipeline UI**: Similar to CI/CD pipelines (GitHub Actions, GitLab CI)
- **Modern feel**: Clean, minimal, professional enterprise software

---

## Success Criteria

The UI should enable users to:
1. ✅ Quickly understand COBOL program structure through visualizations
2. ✅ Navigate between code and graphs seamlessly
3. ✅ Generate high-quality outputs (docs, user stories, code) with one click
4. ✅ Understand the analysis pipeline and what each step provides
5. ✅ Work efficiently with large COBOL programs (1000+ lines)
6. ✅ Export and share analysis results

---

## Design Deliverables Requested

1. **High-fidelity mockups** for:
   - Main three-panel layout
   - Each graph type visualization (AST, CFG, DFG, PDG)
   - Output generation panels
   - Pipeline progress indicator

2. **Component library**:
   - Graph node styles
   - Edge/connection styles
   - Button styles
   - Panel styles
   - Code editor styling

3. **Interaction prototypes** (if possible):
   - Click node → highlight code
   - Tab switching between graphs
   - Pipeline step progression

4. **Responsive layouts** for tablet and mobile

---

**Note**: This prompt is designed for AI design tools. Feel free to adapt visualizations based on the specific graph rendering capabilities and user testing feedback.

