# Plan: Create llm.txt for TJDFT API

**Date:** 2026-03-10
**Complexity:** LOW
**Scope:** 1 new file, referencing existing docs

---

## Context

The TJDFT API project needs an `llm.txt` file -- a concise context document optimized for AI agents that need to interact with the project's APIs. The project already has extensive documentation in `docs/tjdft_apis_completo.md` (353 lines) and `docs/tjdft_api_dictionary.json`, but these are too verbose for quick LLM consumption. The `llm.txt` standard provides a compact, machine-readable summary.

### Existing documentation assets
- `docs/tjdft_apis_completo.md` -- full API documentation (all endpoints, fields, examples)
- `docs/tjdft_api_dictionary.json` -- structured dictionary with valid values for all filter fields
- `CLAUDE.md` -- development-focused instructions for Claude Code
- `README.md` -- project overview and setup

---

## RALPLAN-DR Summary

### Principles (4)
1. **Conciseness over completeness** -- LLMs have limited context windows; every token must earn its place
2. **Actionable over descriptive** -- include what an agent needs to make API calls, not project history
3. **Gotchas first** -- surface known pitfalls (date filter 500 error, 0-indexed pagination, max 40) prominently
4. **Pointer-based depth** -- keep the llm.txt lean, point to detailed docs for exhaustive lists

### Decision Drivers (top 3)
1. **Token efficiency** -- the file must fit comfortably in a single LLM context pass (<2000 lines)
2. **Immediate usability** -- an agent reading this file should be able to make correct API calls without reading any other file
3. **Maintainability** -- the file should be easy to update when APIs change, with minimal duplication of existing docs

### Option A: Markdown format at project root (`llm.txt` with markdown syntax)
- **Pros:** Human-readable, supports headers/tables/code blocks, follows the llm.txt convention (plain text file, markdown content), lives at project root for easy discovery
- **Cons:** Not as structured as YAML/JSON for programmatic parsing
- **Verdict:** CHOSEN -- aligns with the llm.txt standard (https://llmstxt.org/), best balance of readability and structure

### Option B: YAML format (`llm.yaml` or embedded YAML in llm.txt)
- **Pros:** Strictly structured, easy to parse programmatically
- **Cons:** Deviates from the llm.txt convention, harder to read for humans, YAML syntax errors are easy to introduce
- **Verdict:** Rejected -- the convention is specifically `llm.txt` with markdown content; YAML adds friction without clear benefit for LLM consumption

---

## Work Objectives

Create a single `llm.txt` file at the project root that gives any AI agent enough context to correctly use both the Jurisprudence API and RH APIs, while knowing the critical pitfalls.

---

## Guardrails

### Must Have
- File named `llm.txt` at project root (`/Users/gabrielramos/tjdft-api/llm.txt`)
- Markdown-formatted content following llm.txt convention
- All API endpoints with method, URL, and purpose
- Request/response structure for the Jurisprudence search API (the primary API)
- All valid filter fields with brief descriptions
- Known limitations and gotchas (date filter 500, max 40, 0-indexed pagination)
- Pointers to detailed docs (`docs/tjdft_apis_completo.md`, `docs/tjdft_api_dictionary.json`)
- At least 2 working curl/JSON examples for common use cases

### Must NOT Have
- Full lists of 228 relatores, 125 classes, etc. (point to metadata endpoint and dictionary file instead)
- Duplicated content from CLAUDE.md (development setup, testing commands, code patterns)
- Implementation details of the Python client (that belongs in CLAUDE.md)
- Excessive prose or explanatory text -- keep it reference-style

---

## Task Flow

### Step 1: Create llm.txt with structured sections
**File:** `/Users/gabrielramos/tjdft-api/llm.txt`

**Sections in order:**

1. **Header** -- Project name, one-line description, what this file is
2. **Project Purpose** -- 2-3 sentences on what TJDFT API does
3. **API 1: Jurisprudence** (primary)
   - GET endpoint (metadata) -- URL, what it returns, key counts (228 relatores, 125 classes, 33 orgaos)
   - POST endpoint (search) -- URL, full request body schema, all valid `termosAcessorios` fields
   - Response structure -- key fields of a registro (acord ao)
   - Differences for decisoes monocraticas (missing/extra fields)
   - Working examples (3-4 JSON payloads: simple search, filtered search, combined filters, monocraticas)
4. **API 2: RH (Human Resources)** -- base URL, table of all endpoints with method/URL/description, brief field descriptions for key endpoints
5. **Critical Gotchas** -- numbered list of the most important things to know (date filter breaks, pagination 0-indexed, max 40, query can be empty, name matching must be exact)
6. **Detailed References** -- pointers to `docs/tjdft_apis_completo.md`, `docs/tjdft_api_dictionary.json`, and the metadata endpoint for live values

**Acceptance criteria:**
- File exists at project root
- Contains all 6 sections above
- Total length between 150-350 lines (concise but complete)
- All URLs, field names, and constraints are factually correct per existing docs
- An agent reading only this file can construct a valid POST to the search API

### Step 2: Validate accuracy against source docs
Cross-check every URL, field name, constraint, and example in `llm.txt` against:
- `docs/tjdft_apis_completo.md` (ground truth)
- `docs/tjdft_api_dictionary.json` (valid field values)
- `app/services/tjdft_client.py` (client implementation)

**Acceptance criteria:**
- Zero factual discrepancies between llm.txt and source docs
- All JSON examples are valid JSON
- No deprecated or incorrect field names

### Step 3: Add llm.txt reference to README.md
Add a one-line entry in the README documentation section pointing to `llm.txt` for AI agent context.

**Acceptance criteria:**
- README.md mentions llm.txt in the documentation section
- Does not duplicate llm.txt content

---

## Success Criteria

1. `llm.txt` exists at `/Users/gabrielramos/tjdft-api/llm.txt`
2. An AI agent reading only `llm.txt` can correctly construct API calls to both Jurisprudence and RH endpoints
3. All critical gotchas (date filter 500, 0-indexed pagination, max 40/page, exact name matching) are surfaced
4. File is 150-350 lines of markdown
5. Zero factual errors vs. source documentation
6. README references the file

---

## ADR

- **Decision:** Create `llm.txt` at project root using markdown format following the llm.txt convention
- **Drivers:** Token efficiency for LLM consumption, immediate usability without reading other files, maintainability
- **Alternatives considered:** YAML format (`llm.yaml`) -- rejected because it deviates from the llm.txt standard and adds parsing friction without clear benefit
- **Why chosen:** Markdown in a `.txt` file is the established convention (llmstxt.org), maximizes readability for both humans and LLMs, and requires no special tooling
- **Consequences:** Need to manually keep llm.txt in sync when APIs change; mitigated by keeping it lean and pointer-based
- **Follow-ups:** Consider adding a CI check that validates llm.txt URLs are still reachable; consider auto-generating parts from the dictionary JSON in the future
