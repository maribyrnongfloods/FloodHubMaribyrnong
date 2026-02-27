# Lessons Learned

_(Updated after user corrections — patterns to avoid repeating)_

## Session: Feb 2026

### L1 — Follow the Task Management workflow
**Mistake:** Was not writing plans to `tasks/todo.md` or updating `tasks/lessons.md`.
In-context TodoWrite disappears when the conversation ends.
**Rule:** Always create `tasks/todo.md` before starting non-trivial work.
Always update `tasks/lessons.md` after any user correction.

### L2 — CLAUDE.md had stale gauge count
**Pattern:** CLAUDE.md said "10 gauges" but gauges_config.py and tests had 12.
**Rule:** When gauge count changes, update CLAUDE.md at the same time as gauges_config.py
and tests. Single source of truth for documentation.
