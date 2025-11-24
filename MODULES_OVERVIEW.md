# Modules Currently Under Development

## 1. MCP Client (Frontend)

-   Built with **React + TypeScript**
-   Currently in development
-   Focus first on **core functionality**
-   Final UI/UX design will be completed **after all features are stable
    and tested**

## 2. MCP Server (Core Platform)

-   Designed to support **reverse engineering of any programming
    language**
-   Implemented in **Python**, using **PostgreSQL** and potentially a
    **NoSQL database**
-   Approximately **85% complete** and fully functional
-   Tested with multiple MCP clients and **multiple protocols (STDIO,
    Streamable HTTP, SSE)**
-   Most tools already implemented
-   Processing done **locally using compiler algorithms**, AI only when
    necessary
-   **Graph-building tool** included
-   **Observability**:
    -   Execution metadata (runtime, runs, errors)
    -   Prometheus metrics for SRE/dashboard analysis
-   **Tools configured via JSON** (enable/disable, metadata)
-   **Recursive COBOL directory scanner**
-   COBOL metadata generation:
    -   Complexity, lines, clauses, relationships
-   All analysis results persisted to database
-   Pre-analysis for COBOL clause detection and COPY/COPYBOOK generation
-   **Agent system being implemented**:
    -   File analysis and complexity-based workflow selection
    -   Tool selection and execution ordering
-   Artifact storage tool (possibly NoSQL)

## 3. Backend (Supporting Services)

-   Implemented in **Node.js**
-   Uses **NoSQL DB**

## 4. Infrastructure / DevOps / SRE

-   **Kubernetes**, **Docker**, **Terraform**
-   Pre-commit hooks
-   CI/CD pipeline
-   Logging, monitoring, metrics
-   Supports multiple MCP servers (General, IO, Kubernetes-specific,
    etc.)

## 5. Team Skill Requirements

-   **Frontend Engineer** (React/TS)
-   **Backend Engineer** (Node.js)
-   **AI Engineer** (MCP, agents, compilers, LLM)
-   **DevOps/SRE Engineer**
-   **Database Engineer** (PostgreSQL + NoSQL)
