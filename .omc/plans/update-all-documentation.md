# Plan: Hybrid Documentation Update - TJDFT API

**Generated:** 2026-03-11
**Mode:** Consensus (RALPLAN-DR)
**Approach:** Hybrid (high-value/low-maintenance + automation first)

---

## RALPLAN-DR Summary

### Principles (5)
1. **Single Source of Truth** - Each piece of information has one canonical location
2. **Documentation Reflects Code** - All docs match current implementation
3. **Progressive Disclosure** - Overview first, details linked
4. **Automation Over Manual Maintenance** - CI checks prevent future drift
5. **Opportunistic Documentation** - Document when changing, not in big batches

### Decision Drivers (Top 3)
1. **Accuracy** - Documentation must match the actual codebase
2. **Sustainability** - Automation prevents recurring drift
3. **ROI on Effort** - Focus on high-impact, low-maintenance items

### Options Analysis

#### Option A: Comprehensive Update (REJECTED after Architect steelman)
- Update all root-level docs (9 files)
- Update all docs/ files (10 files)
- Full MCP documentation suite
- Manual status updates for all plan files

**Steelman Argument FOR Comprehensive Update:** Most thorough, ensures all documentation is accurate and consistent. The MCP layer is a significant feature that needs proper documentation.

**Why REJECTED:** Architect's steelman analysis revealed that comprehensive updates create temporary accuracy at high cost, then drift again. **Opportunistic documentation** (update when code changes) is more sustainable. Full MCP docs (60% of effort) lack clear ROI—users can read contract.md and quickstart.md. Plan files are historical artifacts; full status updates add noise.

#### Option B: Targeted Critical Updates (REJECTED)
- Focus only on root docs
- Add MCP documentation
- Update plan status
- Remove temp files

**Why REJECTED:** Still includes MCP documentation without automation-first approach.

#### Option C: Hybrid + Automation First (SELECTED)
- **DO:** High-value/low-maintenance (MCP implementation.md, ARCHITECTURE.md, DEVELOPMENT.md uv, version fix, typos)
- **SIMPLIFY:** Plan files with minimal headers (not full status rewrites)
- **AUTOMATE:** CI checks as PRIMARY task (not follow-up)
- **DEFER:** Full MCP tool catalog, README MCP expansion (can be done when MCP changes)

**Why SELECTED:** Addresses immediate gaps while building sustainable infrastructure. CI checks prevent recurring issues. Minimal plan updates respect their role as historical artifacts. Reduced MCP scope acknowledges existing contract.md coverage.

### ADR (Architecture Decision Record)

**Decision:** Hybrid documentation update with automation as primary task

**Drivers:**
- MCP code exists in `app/mcp/` (12 files, ~3000 LOC) but lacks usage guide
- Version mismatch: `pyproject.toml` has `0.1.0`, `config.py` has `1.0.0`
- Date typo in `api_reference.md`: "11/03/2026" (future date)
- Plan files have outdated status but represent historical decisions
- No CI to prevent recurring drift

**Alternatives Considered:**
1. **Comprehensive update** - Rejected per steelman: high effort, temporary accuracy
2. **Targeted updates** - Rejected: doesn't address root cause (no automation)
3. **Do nothing** - Rejected: drift will worsen

**Why Chosen:** Hybrid approach maximizes ROI by:
- Fixing immediate issues (versions, dates, typos)
- Adding ONE high-value MCP doc (implementation guide)
- Building CI automation for sustainable maintenance
- Respecting plan files as historical artifacts

**Consequences:**
- **Positive:** Critical gaps fixed quickly (~2 hours vs 5)
- **Positive:** CI prevents future version/date drift
- **Positive:** Plan files preserved as historical records
- **Positive:** Reduced MCP scope acknowledges existing docs
- **Negative:** Full tool catalog deferred until MCP changes
- **Negative:** README MCP section minimal (links to existing docs)

**Follow-ups:**
- Add pre-commit hook for Markdown linting (Chinese character detection)
- Consider automated MCP doc generation from schemas
- Schedule quarterly documentation reviews

---

## Current State Analysis

### Files Inventory

**Root Level (9 files):**
| File | Status | Action |
|------|--------|--------|
| `README.md` | Good | Minor MCP link addition |
| `CLAUDE.md` | Good | Already mentions MCP |
| `ARCHITECTURE.md` | Good | Add MCP layer to structure |
| `DEVELOPMENT.md` | Needs Update | Replace all `pip` with `uv` |
| `DEPLOYMENT.md` | Good | No change |
| `AGENTS.md` | Good | No change |
| `GEMINI.md` | Needs Fix | Line 168: "命名ação" → "nomenclatura" (IME issue) |
| `tjdft-mcp-plan.md` | Historical | Add implementation header (minimal update) |
| `test-pyramid-plan.md` | Historical | Add progress header (minimal update) |
| `analisecoderabbit_debug.md` | DELETE | Temporary file |

**docs/ Directory (10 files):**
| File | Status | Action |
|------|--------|--------|
| `api_reference.md` | Minor Issue | Date: "11/03/2026" → audit needed |
| `tjdft_api.md` | Good | No change |
| `tjdft_apis_completo.md` | Good | No change |
| `MANUAL_TESTING_GUIDE.md` | Obsolete | Archive to `docs/archive/` |
| `testing-backend-strategy.md` | Good | No change |
| `testing-taxonomy.md` | Good | No change |
| `e2e-test-plan.md` | Good | No change |
| `mcp/quickstart.md` | Good | No change |
| `mcp/configuration.md` | Good | No change |
| `mcp/contract.md` | Minor Issue | Date: "11/03/2026" → audit needed |
| `mcp/implementation.md` | CREATE | New: architecture/usage guide |
| `mcp/tool_catalog.md` | DEFER | Existing contract.md covers this |

### Critical Findings

1. **MCP Implementation Exists But Not Documented**
   - `app/mcp/` has 12 Python files (~3000 LOC)
   - `docs/mcp/contract.md` and `quickstart.md` exist but lack architectural overview
   - **Decision:** Create ONE `implementation.md` with architecture + usage, defer full catalog

2. **Version Inconsistency**
   - `pyproject.toml`: `version = "0.1.0"`
   - `app/config.py`: `app_version` defaults to `"1.0.0"`
   - **Root cause:** No CI check to prevent drift

3. **Date Issues**
   - `docs/api_reference.md`: "11/03/2026" (future date)
   - `docs/mcp/contract.md`: "11/03/2026" (future date)
   - **Root cause:** Manual entry, no validation
   - **Decision:** Audit ALL .md files for dates, establish format policy

4. **Language Issue (IME)**
   - `GEMINI.md` line 168: "命名ação" (Chinese "命名" + Portuguese "ção")
   - **Root cause:** IME auto-completion mishap
   - **Decision:** Fix + consider linter rule

5. **Plan Files Lifecycle**
   - `tjdft-mcp-plan.md`, `test-pyramid-plan.md` have outdated status
   - **Decision:** Add minimal headers, preserve as historical artifacts

---

## Tasks

### T1: Clean up temporary and obsolete files
- **depends_on**: []
- **location**: Root directory, `docs/`
- **description**: Remove temporary files, archive PR-specific docs
- **actions**:
  - [ ] Create `docs/archive/` directory if it doesn't exist
  - [ ] Delete `analisecoderabbit_debug.md` (CodeRabbit output)
  - [ ] Archive `docs/MANUAL_TESTING_GUIDE.md` to `docs/archive/`
  - [ ] Remove `.claude.backup-2026-03-03T19-37-52/` directory
- **validation**: Files removed, `docs/archive/` created with archived file
- **status**: Not Started
- **effort**: 10 min

### T2: Fix version consistency + add CI check
- **depends_on**: []
- **location**: `pyproject.toml`, `app/config.py`, `.github/workflows/`
- **description**: Sync versions AND prevent future drift with automation
- **actions**:
  - [ ] Decide on correct version using semantic versioning criteria:
      - MAJOR bump for breaking changes
      - MINOR bump for new features (MCP qualifies as minor)
      - PATCH bump for bugfixes only
      - Current: `0.1.0` → Recommended: `0.2.0` (MCP is new feature)
  - [ ] Update `pyproject.toml` `version` field
  - [ ] Update `app/config.py` `app_version` default to match
  - [ ] Create `.github/workflows/doc-check.yml` for version consistency
  - [ ] Add CI job that compares `pyproject.toml` version with `app/config.py`
- **validation**: Versions match, CI workflow created and tested
- **status**: Not Started
- **effort**: 25 min

### T3: Audit and fix ALL date issues
- **depends_on**: [T1]
- **location**: User-facing `.md` files only
- **description**: Comprehensive date audit with format policy
- **actions**:
  - [ ] Search `.md` files EXCLUDING generated/internal directories:
      - EXCLUDE: `.claude/` (agent-generated, internal)
      - EXCLUDE: `.claude.backup-*` (backup directories)
      - EXCLUDE: `.omc/` (OMC internal files)
      - INCLUDE: `*.md` (root level)
      - INCLUDE: `docs/*.md`
      - INCLUDE: `docs/mcp/*.md`
  - [ ] Run targeted grep for documentation metadata patterns (not API examples):
      ```bash
      grep -rn --include="*.md" --exclude-dir=".claude" --exclude-dir=".omc" \
        -E "(Last Update|Generated|Updated|Date:).*[0-9]{4}[-/][0-9]{2}[-/][0-9]{2}" . \
        | grep -v ".claude.backup-"
      ```
  - [ ] Fix any future dates (2026 → 2025 or earlier)
  - [ ] Known fixes: `docs/api_reference.md`, `docs/mcp/contract.md`
  - [ ] Fix `GEMINI.md` line 168: "命名ação" → "nomenclatura"
  - [ ] Establish date format policy: ISO 8601 (YYYY-MM-DD)
  - [ ] Document policy in `.omc/docs-style-guide.md` (new file)
- **validation**: No future dates in user-facing .md, style guide created
- **status**: Not Started
- **effort**: 20 min

### T4: Update DEVELOPMENT.md for uv workflow
- **depends_on**: []
- **location**: `DEVELOPMENT.md`
- **description**: Replace ALL pip references with uv commands
- **actions**:
  - [ ] Search for all `pip` occurrences
  - [ ] Replace with `uv` equivalents
  - [ ] Ensure command examples match README.md style
  - [ ] Verify commands: setup, install, run, test
- **validation**: No `pip` references, all commands use `uv`
- **status**: Not Started
- **effort**: 15 min

### T5: Add minimal headers to plan files
- **depends_on**: []
- **location**: `tjdft-mcp-plan.md`, `test-pyramid-plan.md`
- **description**: Add brief implementation notes without rewriting all status
- **actions**:
  - [ ] Locate the "**Generated**: [date]" line (typically line 3) in each file
  - [ ] Add a new line immediately AFTER the "**Generated**" line
  - [ ] Format: `**Status**: [status text]`
  - [ ] For `tjdft-mcp-plan.md`: Add `**Status**: IMPLEMENTED (see app/mcp/)`
  - [ ] For `test-pyramid-plan.md`: Add `**Status**: T0-T5 complete, T6-T11 deferred`
  - [ ] Do NOT modify any individual task statuses (preserve historical record)
- **validation**: Headers added in correct location, task statuses unchanged
- **status**: Not Started
- **effort**: 10 min

### T6: Create MCP implementation guide
- **depends_on**: []
- **location**: `docs/mcp/implementation.md` (new file)
- **description**: Architectural overview + usage guide (NOT full tool catalog)
- **actions**:
  - [ ] Document `app/mcp/` directory structure
  - [ ] Document MCP runtime lifecycle (startup, request handling, shutdown)
  - [ ] List available tools with ONE-line descriptions
  - [ ] Add basic usage example (echo client or Claude Desktop config)
  - [ ] Link to existing `contract.md` for detailed tool specs
  - [ ] Add troubleshooting section (common issues)
  - [ ] ROI check: If existing docs cover 80%, keep this minimal
- **validation**: File created, examples tested, links working
- **status**: Not Started
- **effort**: 45 min (reduced from 60 min)

### T7: Update ARCHITECTURE.md for MCP layer
- **depends_on**: [T6]
- **location**: `ARCHITECTURE.md`
- **description**: Add MCP to system architecture
- **actions**:
  - [ ] Add `app/mcp/` to project structure section
  - [ ] Add MCP runtime to components diagram/description
  - [ ] Link to `docs/mcp/implementation.md`
- **validation**: ARCHITECTURE.md mentions MCP with link
- **status**: Not Started
- **effort**: 15 min

### T8: Minimal README.md MCP addition
- **depends_on**: [T6]
- **location**: `README.md`
- **description**: Add MCP to docs list (NOT new section)
- **actions**:
  - [ ] Verify MCP is in feature list
  - [ ] Add "MCP (Model Context Protocol)" to documentation list
  - [ ] Link to `docs/mcp/quickstart.md` and `docs/mcp/implementation.md`
- **validation**: README links to MCP docs
- **status**: Not Started
- **effort**: 5 min

### T9: Create Markdown linting configuration
- **depends_on**: []
- **location**: `.markdownlint.json`
- **description:** Prevent IME/language mixing issues
- **actions**:
  - [ ] Create `.markdownlint.json` with Portuguese-friendly rules
  - [ ] Add rule to detect unexpected non-ASCII (CJK) characters in Portuguese docs
  - [ ] Document in `.omc/docs-style-guide.md`
- **validation:** Linter config created, documented
- **status:** Not Started
- **effort:** 15 min

### T10: Final verification
- **depends_on**: [T1, T2, T3, T4, T5, T6, T7, T8, T9]
- **location**: All modified files
- **description**: Verify changes and run CI
- **actions**:
  - [ ] Run CI workflow for version check
  - [ ] Spot-check all modified files
  - [ ] Run `uv run pytest` to ensure no breakage
  - [ ] Verify all new links resolve
- **validation**: CI passes, tests pass, links work
- **status**: Not Started
- **effort**: 15 min

---

## Parallel Execution Groups

| Wave | Tasks | Can Start When |
|------|-------|----------------|
| 1 | T1, T2, T4, T5, T9 | Immediately (independent) |
| 2 | T3 | After T1 complete (backup dir removed) |
| 3 | T6 | After T1-T5, T9 complete |
| 4 | T7, T8 | After T6 complete |
| 5 | T10 | All previous tasks complete |

---

## CI Automation: Version Check

**File:** `.github/workflows/doc-check.yml`

```yaml
name: Documentation Consistency Check

on:
  pull_request:
    paths:
      - 'pyproject.toml'
      - 'app/config.py'
      - '**.md'
  push:
    paths:
      - 'pyproject.toml'
      - 'app/config.py'

jobs:
  version-consistency:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Extract version from pyproject.toml
        run: |
          VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
          echo "PYPROJECT_VERSION=$VERSION" >> $GITHUB_ENV
      - name: Extract version from app/config.py
        run: |
          VERSION=$(grep -A2 'app_version:' app/config.py | grep 'default=' | sed 's/.*default="\([^"]*\)".*/\1/')
          echo "CONFIG_VERSION=$VERSION" >> $GITHUB_ENV
      - name: Compare versions
        run: |
          if [ "$PYPROJECT_VERSION" != "$CONFIG_VERSION" ]; then
            echo "Version mismatch: pyproject.toml=$PYPROJECT_VERSION, config.py=$CONFIG_VERSION"
            exit 1
          fi
          echo "Versions match: $PYPROJECT_VERSION"
```

---

## Date Format Policy

**File:** `.omc/docs-style-guide.md` (new)

```markdown
# Documentation Style Guide

## Date Format

All dates in documentation MUST use ISO 8601 format: `YYYY-MM-DD`

Examples:
- ✅ `2026-03-11`
- ❌ `11/03/2025`
- ❌ `March 11, 2025`

## Language

- Technical documentation: Portuguese
- Code comments: English
- Mixed language not allowed (e.g., "命名ação")

## Version Sync

When updating versions:
1. Update `pyproject.toml`
2. Update `app/config.py` `app_version` default
3. Update any docs that mention version
```

---

## Markdown Linting Configuration

**File:** `.markdownlint.json` (new)

```json
{
  "default": true,
  "MD013": {
    "line_length": 120,
    "code_blocks": false,
    "tables": false
  },
  "MD033": false,
  "no-hard-tabs": false,
  "whitespace": false
}
```

**Note:** For CJK character detection (IME mixing), consider adding a pre-commit hook or CI check that uses `grep -P '[\x{4e00}-\x{9fff}]'` to detect unexpected Chinese characters in Portuguese documentation files.

---

## Deferred Items

| Item | Why Deferred | Trigger |
|------|-------------|---------|
| Full MCP tool catalog | `contract.md` already covers tools | When MCP tools change significantly |
| README MCP section expansion | Quickstart exists, low ROI | When MCP usage patterns emerge |
| CLAUDE.md MCP update | Already mentions MCP | Not urgent |
| Pre-commit hook | Nice-to-have, CI sufficient | When onboarding new contributors |

---

## File-by-File Action Summary

### Root Level

| File | Action | Details |
|------|--------|---------|
| `README.md` | Minimal update | Add MCP links (T8) |
| `CLAUDE.md` | No change | Already mentions MCP |
| `ARCHITECTURE.md` | Update | Add MCP layer (T7) |
| `DEVELOPMENT.md` | Update | Replace pip with uv (T4) |
| `DEPLOYMENT.md` | No change | Already accurate |
| `AGENTS.md` | No change | Already accurate |
| `GEMINI.md` | Fix | Line 168: "命名ação" → "nomenclatura" (T3) |
| `tjdft-mcp-plan.md` | Minimal | Add header only (T5) |
| `test-pyramid-plan.md` | Minimal | Add header only (T5) |
| `analisecoderabbit_debug.md` | DELETE | Temporary file (T1) |

### docs/ Directory

| File | Action | Details |
|------|--------|---------|
| `api_reference.md` | Audit | Date fix if needed (T3) |
| `tjdft_api.md` | No change | Already accurate |
| `tjdft_apis_completo.md` | No change | Already accurate |
| `MANUAL_TESTING_GUIDE.md` | Archive | Move to docs/archive/ (T1) |
| `testing-backend-strategy.md` | No change | Already accurate |
| `testing-taxonomy.md` | No change | Already accurate |
| `e2e-test-plan.md` | No change | Reference for future |
| `mcp/quickstart.md` | No change | Already accurate |
| `mcp/configuration.md` | No change | Already accurate |
| `mcp/contract.md` | Audit | Date fix if needed (T3) |
| `mcp/implementation.md` | CREATE | New: architecture + usage (T6) |

### Configuration / CI

| File | Action | Details |
|------|--------|---------|
| `.github/workflows/doc-check.yml` | CREATE | CI version check (T2) |
| `.markdownlint.json` | CREATE | Markdown linter config (T9) |
| `.omc/docs-style-guide.md` | CREATE | Style guide (T3) |
| `pyproject.toml` | Update | Version consistency (T2) |
| `app/config.py` | Update | Version consistency (T2) |

---

## Success Criteria

1. All temporary files removed or archived (docs/archive/ created, backup dirs removed)
2. Version numbers consistent using semantic versioning criteria
3. CI check created and passing with WORKING grep pattern for multi-line config.py
4. User-facing .md files audited for dates (excludes .claude/, .claude.backup-*, .omc/)
5. Date grep uses targeted metadata patterns (not broad API example matching)
6. No mixed-language text (IME issue fixed)
7. MCP implementation guide created (minimal, not exhaustive)
8. Plan files have headers added after "**Generated**" line (statuses preserved)
9. DEVELOPMENT.md uses uv consistently
10. Markdown linting config created with example content provided
11. All changes verified with tests

---

## ROI Comparison: Original vs Hybrid

| Aspect | Original (Comprehensive) | Hybrid (Revised) |
|--------|--------------------------|------------------|
| MCP Documentation | 105 min (2 files, catalog) | 45 min (1 file, guide only) |
| Plan Files | 30 min (full status rewrite) | 10 min (headers only) |
| Version Sync | 10 min (manual) | 25 min (manual + CI) |
| Dates | 10 min (known fixes) | 20 min (comprehensive audit) |
| **Total Effort** | **~5 hours** | **~2.5 hours** |
| **Sustainability** | Low (drifts again) | High (CI prevents drift) |
| **Plan Files** | Obscured history | Preserved as artifacts |

---

## Estimated Effort

| Task | Estimated Time |
|------|----------------|
| T1: Cleanup | 10 min |
| T2: Version sync + CI | 25 min |
| T3: Date audit + fixes | 20 min |
| T4: DEVELOPMENT.md uv | 15 min |
| T5: Plan file headers | 10 min |
| T6: MCP implementation guide | 45 min |
| T7: ARCHITECTURE.md MCP | 15 min |
| T8: README MCP links | 5 min |
| T9: Markdown linter config | 15 min |
| T10: Final verification | 15 min |
| **Total** | **~2.5 hours** |

---

## Steelman Response: Why Not Comprehensive?

**Argument FOR Comprehensive:** "Most thorough, ensures all documentation is accurate."

**Counter-argument (Architect's steelman):**
1. **Temporary Accuracy:** Comprehensive updates create a snapshot that immediately begins drifting
2. **High Cost:** 5 hours for documentation that could be automated
3. **False Completeness:** Full tool catalogs become outdated when tools change
4. **Obscured History:** Rewriting plan file status loses historical context

**Hybrid Approach Benefits:**
- **CI First:** Automation prevents recurring issues (versions, dates)
- **Minimal Viable:** One MCP guide + existing docs = 80% value at 20% cost
- **Historical Respect:** Plan files keep original status, headers show current state
- **Sustainable:** Less effort means more frequent updates possible

---

## References

- `app/mcp/` - MCP implementation source
- `pyproject.toml` - Version source of truth
- `app/config.py` - Settings definition
- `docs/mcp/` - Existing MCP contract/config docs
- `.claude/agents/` - Agent definitions
