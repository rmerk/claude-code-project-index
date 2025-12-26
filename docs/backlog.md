# Engineering Backlog

This backlog collects cross-cutting or future action items that emerge from reviews and planning.

Routing guidance:

- Use this file for non-urgent optimizations, refactors, or follow-ups that span multiple stories/epics.
- Must-fix items to ship a story belong in that story's `Tasks / Subtasks`.
- Same-epic improvements may also be captured under the epic Tech Spec `Post-Review Follow-ups` section.

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
| ---- | ----- | ---- | ---- | -------- | ----- | ------ | ----- |
| 2025-11-01 | 1.4 | 1 | Enhancement | Low | TBD | Open | Consider adding file size limits to `load_detail_module()` for DoS prevention. Add `max_size_mb` parameter with reasonable default (e.g., 10MB). Check file size before `json.load()` at `scripts/loader.py:82`. Current impact: Low (detail modules typically <10KB). |
| 2025-11-01 | 1.4 | 1 | Documentation | Low | TBD | Open | Document performance characteristics in project README. Current performance: 5ms average load time (100x better than 500ms requirement). Help users optimize agent query strategies with actual metrics. |
| 2025-11-01 | 1.4 | 1 | Enhancement | Low | TBD | Open | Consider caching strategy for production agents. Multiple queries may load same modules repeatedly. Simple in-memory dict cache with TTL could improve performance further. Current impact: None (performance already excellent). Future enhancement for high-frequency queries. |
| 2025-11-01 | 1.6 | 1 | Testing | Medium | TBD | Open | Add integration test file `scripts/test_integration_legacy.py` to verify agent analysis works with legacy format. Current gap: AC#3 cannot be fully verified without integration tests. Unit tests pass (10/10) but agent workflow not tested. File: scripts/ |
| 2025-11-01 | 1.6 | 1 | Testing | Medium | TBD | Open | Add integration test for agent migration suggestions. Verify >1000 file threshold triggers suggestion correctly. Test that "once per session" logic works. File: scripts/test_index_analyzer_agent.py |
| 2025-11-01 | 1.6 | 1 | Testing | Low | TBD | Open | Add integration test for agent split format workflow. Verify lazy-loading works correctly when split architecture detected. File: scripts/test_index_analyzer_agent.py |
| 2025-11-13 | TBD | TBD | Enhancement | Low | TBD | Open | **Ultra-Minimal Core Mode**: Add config option `minimal_core: true` to omit 'f' key entirely from core index. When enabled, core would shrink from 57 KB to ~20 KB (tree + modules + file_to_module_map + stats only). Trade-offs: (1) ✅ Faster direct file queries (126 KB vs 163 KB), (2) ✅ Smaller core load (20 KB vs 57 KB), (3) ❌ Slower relevance-scored queries (must load all modules to get git metadata), (4) ❌ Less effective temporal awareness without upfront git metadata. Recommendation: Optional feature for users who prioritize minimal context over intelligent relevance scoring. Default: keep current 57 KB core with Epic 2 intelligence features. Implementation: Modify `generate_split_index()` to skip 'f' key population when config flag set. Files: scripts/project_index.py, .project-index.json schema. |
