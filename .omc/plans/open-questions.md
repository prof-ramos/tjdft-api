# Open Questions

## TJDFT Quick Wins Revised - 2026-03-10

- [x] Should `resumo_relevancia` include full ementa or just snippets? — **Decision:** Just snippets from `marcadores`, full ementa only on detail endpoint
- [x] Should `densidade.alerta` be configurable? — **Decision:** Hardcoded for now, can be made configurable later
- [x] Should we add a detail endpoint for full decision view? — **Decision:** Future enhancement, not in this quick-wins scope

## Quick Wins Features (Previous - Deprecated) - 2026-03-10

> These questions are archived for historical context only. They were superseded by the revised quick-wins scope above and no further action is planned here unless the scope is reopened.

- [ ] Should keyword highlighting support case-insensitive matching only, or also regex patterns? — Affects `add_keyword_highlights` implementation complexity
- [ ] What should be the default `min_match_score` for similarity filtering? — Currently 0.3; may need tuning based on usage
- [ ] Should we add a "fetch all pages" option for users who want complete filtered results? — Would address pagination limitation but increases API quota usage
