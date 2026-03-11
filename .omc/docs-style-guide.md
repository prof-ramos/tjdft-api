# Documentation Style Guide

## Markdown Linting Configuration

The project uses `.markdownlint.json` for consistent Markdown formatting across documentation files.

### Configuration Rules

- **Default rules**: Enabled
- **MD013 (line-length)**: Set to 120 characters
  - Disabled for code blocks (they may contain longer lines)
  - Disabled for tables (they require specific formatting)
- **MD033 (no-inline-html)**: Disabled (allows inline HTML where needed)
- **no-hard-tabs**: Disabled (allows tabs for consistency with other formatters)
- **whitespace**: Disabled (allows flexible trailing whitespace for formatting)

### CJK Character Detection

When working with Markdown files containing CJK (Chinese, Japanese, Korean) characters or using IME (Input Method Editor):

- Markdown linting tools should detect CJK characters to avoid false positives on line-length rules
- The `MD013` rule may need adjustment for documents with significant CJK content
- Consider using `code_blocks: false` and `tables: false` to prevent issues in mixed-language documents

### Running the Linter

```bash
# Using markdownlint-cli (Node.js)
npx markdownlint '**/*.md' '.github/**/*.md'

# Using markdownlint-cli2 (simplified config)
npx markdownlint-cli2 '**/*.md'
```

### VS Code Integration

Install the [Markdown Lint extension](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) for real-time feedback.

### Pre-commit Hook

To add Markdown linting to pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/igorshubovych/markdownlint-cli
    rev: v0.39.0
    hooks:
      - id: markdownlint
        args: [--config=.markdownlint.json]
```

## Date Format Policy

### Standard Format
All dates in documentation MUST follow ISO 8601 format: `YYYY-MM-DD`

### Date Validation
- Dates must be realistic and not in the future (relative to document creation)
- Review any dates that appear to be in the future relative to when the document was last modified
- Maintain consistency with the document's creation/update timeline

### Common Date Fields
- `Generated:` - For plan/audit documents
- `Date of Last Update:` - For living documents
- `Updated:` - Alternative last update field

### Examples
```markdown
**Generated**: 2026-03-11
**Date of Last Update:** 2026-03-11
```
