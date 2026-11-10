# 03: Pool model and the default pool

**What to build:** A pool is validated as exactly 90 distinct topics, each with an explanation. Its topics fill the nine columns in list order. A read-only default pool is seeded, and the host can see it.

**Blocked by:** 01 (Project skeleton)

**Status:** ready-for-agent

- [x] A pool with 89 or 91 topics is rejected
- [x] A pool with duplicate topics is rejected
- [x] A topic without an explanation is rejected
- [x] Columns hold 9, 10 × 7 and 11 topics in list order
- [x] The default pool is seeded and cannot be edited
- [x] The host can see the default pool's columns and topics
