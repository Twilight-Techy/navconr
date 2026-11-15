# Navconr project documents

Navconr is the working name for a library that lets agents navigate bounded knowledge maps, progressively discover relevant locations, and retrieve exact source evidence.

These documents cover the project from design through implementation, evaluation, visualization, integrations, release, and research publication. They were established on 2026-11-15. The local implementation and software verification are available; research and public-release gates remain open. See STATUS.md and reports for evidence.

| Document | Purpose |
| --- | --- |
| [STATUS.md](STATUS.md) | Implemented capabilities, verification and remaining gates |
| [QUICKSTART.md](QUICKSTART.md) | Run the local library, CLI and inspector |
| [API.md](API.md) | Public tools, provider and agent integrations |
| [ADAPTERS.md](ADAPTERS.md) | Supported formats and fidelity limits |
| [OPERATIONS.md](OPERATIONS.md) | Updates, integrity, backup and data handling |
| [EVALUATION.md](EVALUATION.md) | Reproduce software checks and understand research limits |
| [RELEASE.md](RELEASE.md) | Local artifacts and publication gates |
| [RULES.md](RULES.md) | Engineering invariants, working practices, and completion requirements |
| [MEMORY.md](MEMORY.md) | Durable context, decisions, open questions, current state, and next action |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Scope, architecture, milestones, validation, and release criteria |
| [TASKS.md](TASKS.md) | Ordered executable tasks, dependencies, acceptance criteria, and status |

The original conversation and dumps are retained locally in `context/` and excluded from the public repository.

## Reading and maintenance

At the beginning of a session, read the rules, memory, and relevant tasks. Before implementing a task, check its dependencies and acceptance criteria. At the end of meaningful work, update task status and memory with what actually changed and what should happen next.

`TASKS.md` owns completion status. `MEMORY.md` owns decisions and handoff context. `IMPLEMENTATION_PLAN.md` owns architecture and scope. Update the relevant documents together when a decision changes scope or task order; avoid copying the backlog into memory.

## Current scope

The user authorized building and running the complete project. Local implementation and software checks now exist. The full plan still includes deferred live-model validation, independent research review/study, distribution identity/licensing and public publication/submission gates. See STATUS.md for the distinction between completed local deliverables and open acceptance work.
