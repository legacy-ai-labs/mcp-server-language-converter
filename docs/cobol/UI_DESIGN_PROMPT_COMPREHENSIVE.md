# COBOL Legacy Modernization Platform - UI Design Prompt

## **Platform Overview**
Design a professional, dark-themed web application for modernizing COBOL legacy systems. The platform analyzes COBOL programs through a multi-stage pipeline (AST → CFG → DFG → PDG) and generates modern outputs (documentation, user stories, Java code).

---

## **Core User Journey**

**1. Upload & Parse** → **2. Analyze (visualize graphs)** → **3. Generate Outputs** → **4. Export Results**

---

## **Main UI Layout Structure**

### **Three-Panel Layout (Recommended)**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Header: Logo | "COBOL Modernization Platform" | Upload | Settings │
├──────────────┬──────────────────────────────────┬───────────────────┤
│              │                                  │                   │
│   LEFT       │         CENTER                   │      RIGHT        │
│   PANEL      │         PANEL                    │      PANEL        │
│              │                                  │                   │
│  COBOL       │   Analysis Pipeline &            │   Generated       │
│  Source      │   Graph Visualizations           │   Outputs         │
│  Viewer      │                                  │                   │
│              │   ┌─────────────────────────┐    │                   │
│  • Syntax    │   │  Pipeline Progress      │    │  Tabs:            │
│    highlight │   │  [==============]       │    │  • Documentation  │
│  • Line #s   │   │  AST→CFG→DFG→PDG        │    │  • User Stories   │
│  • Comments  │   └─────────────────────────┘    │  • Java Code      │
│    marked    │                                  │  • Insights       │
│  • Foldable  │   Tab Navigation:                │                   │
│    sections  │   [AST] [CFG] [DFG] [PDG]        │  Export Options:  │
│              │                                  │  [📄] [📊] [💾]    │
│  Metadata:   │   Interactive Graph Display:     │                   │
│  Lines: 234  │   • Node-link diagrams           │  Preview with     │
│  Comments:12 │   • Zoom/pan controls            │  syntax highlight │
│  Divisions:4 │   • Click nodes for details      │  and formatting   │
│              │   • Highlight connections        │                   │
└──────────────┴──────────────────────────────────┴───────────────────┘
```

---

## **Detailed Component Specifications**

### **LEFT PANEL: COBOL Source Viewer**

**Purpose**: Display original COBOL code with enhanced readability

**Features**:
- **Syntax highlighting** (COBOL keywords, divisions, sections)
- **Line numbers** with clickable navigation
- **Comment visualization**:
  - Different colors for comment types (HEADER, TODO, DOCUMENTATION)
  - Inline badges for CRITICAL/IMPORTANT markers
- **Foldable sections** for divisions/sections (click to collapse)
- **Search bar** at top with regex support
- **Metadata panel** at bottom showing:
  - Total lines, comments count, divisions, paragraphs
  - File name, last modified date
  - Detected issues/warnings count

**Visual Style**:
- Dark background (#1a1a1a or similar)
- Monospace font (JetBrains Mono, Fira Code)
- Subtle line number gutter (#2d2d2d)
- Comment text in muted color (#6c757d) with type badges

---

### **CENTER PANEL: Analysis Pipeline & Graph Visualizations**

**Purpose**: Show analysis progress and interactive graph visualizations

#### **Top Section - Pipeline Progress Indicator**:
```
┌────────────────────────────────────────────────────────────┐
│  Analysis Pipeline:                                        │
│  ●────────●────────●────────●────────●                     │
│  Parse   AST     CFG     DFG     PDG    ✓ Complete         │
│                                          (2.3s)            │
└────────────────────────────────────────────────────────────┘
```

#### **Tab Navigation for Graph Types**:
- **[AST Tab]**: Abstract Syntax Tree
- **[CFG Tab]**: Control Flow Graph
- **[DFG Tab]**: Data Flow Graph
- **[PDG Tab]**: Program Dependency Graph

#### **Graph Visualization Area** (per tab):

##### **AST Tab**:
- **Tree layout** showing program structure
- Nodes: Program → Divisions → Sections → Paragraphs → Statements
- **Color coding**:
  - Blue: IDENTIFICATION/ENVIRONMENT divisions
  - Green: DATA division (variables)
  - Orange: PROCEDURE division (logic)
  - Purple: Statements
- **Comments overlay**: Show comment badges attached to nodes
- **Hover**: Display node details (type, location, attributes)
- **Click**: Highlight corresponding code in left panel

##### **CFG Tab**:
- **Directed graph** with flow edges
- Nodes: Basic blocks, decision points (IF, EVALUATE), loops
- **Edge types**:
  - Solid arrow: Sequential flow (gray)
  - Green arrow: True branch
  - Red arrow: False branch
  - Dotted: GOTO/PERFORM jumps
- **Entry/Exit nodes** clearly marked
- **Path highlighting**: Click to highlight execution paths

##### **DFG Tab**:
- **Node-link diagram** showing data dependencies
- Nodes: Variable definitions (circles) and uses (squares)
- **Edges**: Data flow arrows labeled with variable names
- **Color by variable**: Each variable has consistent color
- **Filter controls**: Toggle variable types (input/output/intermediate)

##### **PDG Tab**:
- **Combined graph** showing both control + data dependencies
- **Dual-colored edges**:
  - Blue: Control dependencies
  - Orange: Data dependencies
- **Node clustering**: Group related statements
- **Slice feature**: Click variable to show program slice

#### **Interactive Controls (all tabs)**:
- Zoom: +/- buttons and mouse wheel
- Pan: Click-drag or arrow keys
- Fit to screen button
- Export graph as PNG/SVG
- Mini-map in corner for large graphs
- Legend explaining node/edge types

---

### **RIGHT PANEL: Generated Outputs**

**Purpose**: Display and export generated artifacts

#### **Tab Structure**:

##### **📄 Documentation Tab**:
```
┌─────────────────────────────────────┐
│  Auto-Generated Documentation      │
│  ─────────────────────────────────  │
│                                     │
│  ## ACCOUNT-VALIDATOR               │
│                                     │
│  **Purpose**: Validates customer    │
│  accounts during teller operations  │
│                                     │
│  **Critical Requirements**:         │
│  • Must complete within 200ms       │
│  • IRS compliance required          │
│                                     │
│  **Data Structures**:               │
│  • ACCOUNT-NUMBER (10 digits)       │
│  • ACCOUNT-STATUS (A/C/F)           │
│  ...                                │
└─────────────────────────────────────┘
```

##### **📋 User Stories Tab**:
```
┌─────────────────────────────────────┐
│  User Stories (4 generated)         │
│  ─────────────────────────────────  │
│                                     │
│  ✓ Story 1: Account Validation      │
│  As a: Bank teller                  │
│  I want to: Validate account #s     │
│  So that: Prevent invalid txns      │
│                                     │
│  Acceptance Criteria:               │
│  ☐ Account must be 10 digits        │
│  ☐ Status must be 'A' (active)      │
│  ☐ Response < 200ms                 │
│                                     │
│  [Edit] [Export] [Generate More]    │
│  ─────────────────────────────────  │
│  ⊕ Story 2: Balance Checking...     │
└─────────────────────────────────────┘
```

##### **☕ Java Code Tab**:
```
┌─────────────────────────────────────┐
│  COBOL → Java Conversion            │
│  ─────────────────────────────────  │
│                                     │
│  Quality: ████████░░ 85%            │
│  • Business logic: ✓ Converted      │
│  • Comments: ✓ Preserved            │
│  • Warnings: 2 manual reviews       │
│                                     │
│  [Show Side-by-Side] [Download]     │
│                                     │
│  public class AccountValidator {    │
│      // CRITICAL: IRS compliance    │
│      private Long accountNumber;    │
│      ...                            │
│  }                                  │
└─────────────────────────────────────┘
```

##### **💡 Insights Tab**:
```
┌─────────────────────────────────────┐
│  Analysis Insights                  │
│  ─────────────────────────────────  │
│                                     │
│  Complexity Metrics:                │
│  • Cyclomatic: 12 (Medium)          │
│  • Lines of Code: 234               │
│  • Comment Ratio: 15% (Good)        │
│                                     │
│  Modernization Strategy:            │
│  🎯 Recommended: Refactor + Wrap    │
│  • Break into 3 microservices       │
│  • Extract 5 reusable functions     │
│  • High ROI: 8/10                   │
│                                     │
│  Business Rules Extracted (7):      │
│  • Tax calculation (IRS 2018-15)    │
│  • Account validation (BSA/AML)     │
│  ...                                │
└─────────────────────────────────────┘
```

#### **Export Options** (bottom of panel):
- **📄 PDF**: Complete report
- **📊 Excel**: Metrics spreadsheet
- **💾 Archive**: All artifacts (.zip)
- **🔗 Share**: Generate shareable link

---

## **Visual Design Specifications**

### **Color Palette (Dark Theme)**

#### **Base Colors**:
```
Background:      #0d0d0d (darkest)
Panel BG:        #1a1a1a (dark)
Card BG:         #2d2d2d (medium-dark)
Border:          #404040 (subtle)
Text Primary:    #ffffff (white)
Text Secondary:  #b0b0b0 (gray)
```

#### **Accent Colors**:
```
Primary (Blue):    #4a9eff (interactive elements)
Success (Green):   #4caf50 (completed, valid)
Warning (Orange):  #ff9800 (review needed)
Error (Red):       #f44336 (critical, errors)
Info (Teal):       #00bcd4 (information)
Purple:            #9c27b0 (special features)
```

#### **Graph Node Colors**:
```
AST nodes:
  - Division:    #3f51b5 (indigo)
  - Section:     #2196f3 (blue)
  - Paragraph:   #00bcd4 (cyan)
  - Statement:   #009688 (teal)

CFG nodes:
  - Entry/Exit:  #9c27b0 (purple)
  - Decision:    #ff9800 (orange)
  - Basic block: #4caf50 (green)

DFG nodes:
  - Definition:  #2196f3 (blue)
  - Use:         #ff5722 (deep orange)

PDG nodes:
  - Combined:    #7c4dff (light purple)
```

### **Typography**

```
Headings:       Inter, 16-24px, Bold
Body Text:      Inter, 14px, Regular
Code:           JetBrains Mono, 13px, Regular
Monospace:      Fira Code, 13px (with ligatures)
Small Text:     Inter, 12px, Regular
```

### **Spacing & Layout**

```
Panel Padding:       24px
Card Padding:        16px
Section Margin:      20px
Element Gap:         12px
Border Radius:       8px (cards), 4px (buttons)
```

---

## **Key User Interactions**

### **1. Upload Flow**:
```
Click "Upload" → Drag-drop or Browse → File validation
→ Show preview → Click "Analyze" → Pipeline starts
```

### **2. Analysis Flow**:
```
Pipeline shows progress (animated) → Tabs populate as complete
→ Notification when done → Auto-switch to AST tab
```

### **3. Graph Interaction**:
```
Hover node → Tooltip with details
Click node → Highlight in source (left) + show details popup
Double-click → Zoom to node
Right-click → Context menu (export, copy, etc.)
```

### **4. Cross-Panel Linking**:
```
Click line in source → Highlight in graph
Click graph node → Jump to source line
Click user story → Highlight relevant code sections
```

### **5. Export Flow**:
```
Select output type → Choose format → Preview → Download
or Share link → Copy to clipboard
```

---

## **Special Features to Include**

### **Pipeline Visualization** (center-top):
- Animated progress bar
- Step-by-step completion indicators
- Time elapsed per stage
- Success/warning/error badges

### **Comment Insight Panel** (overlay):
- Show comment distribution
- Highlight TODO/CRITICAL comments
- Comment type breakdown chart

### **Diff View** (for Java conversion):
- Side-by-side COBOL ↔ Java
- Line-by-line mapping
- Highlight differences

### **Search & Filter**:
- Global search across all panels
- Filter graphs by node type
- Filter outputs by category

### **Responsive Behavior**:
- Collapsible panels on smaller screens
- Tabs become dropdowns on mobile
- Graph controls adapt to screen size

---

## **Inspiration References**

Model the UI after these modern dark-themed tools:
- **GitHub's Dark Mode**: Clean, professional, excellent code viewer
- **VS Code UI**: Panel layout, tab structure, command palette
- **Figma**: Canvas manipulation (zoom, pan), layers panel
- **Grafana Dashboards**: Graph visualizations, metric displays
- **Linear**: Modern dark theme, smooth animations, excellent UX

---

## **Technical Visualization Requirements**

### **Graph Rendering**:
- Use **D3.js** or **Cytoscape.js** for interactive graphs
- Force-directed layout for DFG/PDG
- Hierarchical tree layout for AST
- Dagre layout for CFG (directed acyclic)

### **Performance**:
- Handle programs up to 10,000 lines
- Lazy-load graph nodes (virtual scrolling)
- Progressive rendering for large graphs
- Debounced interactions

### **Accessibility**:
- Keyboard navigation for all panels
- Screen reader support for graphs
- High contrast mode toggle
- Focus indicators on interactive elements

---

## **Sample Screens to Design**

**Priority Order**:
1. **Main Analysis View** (3-panel layout as described)
2. **Upload/Landing Page** (drag-drop zone, recent files)
3. **Graph Detail Modal** (expanded view of single graph)
4. **Export Options Screen** (format selection, preview)
5. **Settings Panel** (preferences, analysis options)
6. **Empty States** (no file loaded, analysis pending, no results)

---

## **Final Notes**

**Goal**: Create a tool that feels like a **modern IDE meets data visualization platform**

**Mood**: Professional, trustworthy, powerful yet approachable

**Key Differentiators**:
- **Visual pipeline** showing COBOL transformation stages
- **Interactive graphs** that link to source code
- **AI-powered insights** displayed beautifully
- **Export-ready outputs** with one click

**Avoid**: Cluttered interfaces, overwhelming information, confusing navigation

---

## **Summary**

This design creates a comprehensive COBOL modernization platform with:
- ✅ Clear three-panel layout (Source | Analysis | Outputs)
- ✅ Visual pipeline showing transformation stages
- ✅ Interactive graph visualizations (AST, CFG, DFG, PDG)
- ✅ Multiple output formats (docs, stories, code)
- ✅ Professional dark theme
- ✅ Cross-panel linking and navigation
- ✅ Export and sharing capabilities

The result should be a powerful yet intuitive tool that makes COBOL modernization accessible and efficient.
