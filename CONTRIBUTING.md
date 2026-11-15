# Contributing

Read `AGENTS.md`, project rules and current memory before changes. Install with `make setup`; run `make check`. Browser checks additionally require `cd viewer && npx playwright install chromium && npm test`, the browser suite prepares its own authored fixture database and recorded query.

Add tests for externally visible behavior and meaningful invariants. Keep routine tests offline. Mark optional real-provider and model-download checks separately, with recorded configuration and costs. Do not add private corpora, credentials, generated databases, or unredacted traces to release artifacts.

Source adapter work must preserve original/extracted coordinate distinctions and exact-byte tests. Navigation changes need budget, revision and recovery checks. Evaluator changes need known scoring fixtures and split validation. Schema changes require compatibility decisions and migrations when published schemas exist.

Update tasks and memory with verified work and remaining gaps. Do not mark an acceptance gate complete because its code path exists. Public contributions/publishing policy and license are pending the project's distribution decision.
