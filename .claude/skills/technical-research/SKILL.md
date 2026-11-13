---
name: technical-research
description: Research an external API, SDK, library, CLI or platform behaviour and preserve a concise, sourced local reference. Use when implementation needs external documentation, when a local reference is marked needs-revalidation, or before calling an unfamiliar external service.
metadata:
  harness: "0.1.0"
---

# Technical research

## Order of sources

1. Local first: `harness docs search --type api-reference <tech>` (also `library-reference`, `cli-reference`) and `docs/reference/external/`. If a current reference covers the need, use it and stop.
2. Project evidence: existing code that already calls the API, tests, fixtures, recorded failures (`failed-implementation`).
3. Official documentation of the exact version in use (check lock files, manifests, `version` fields). Prefer official sources over blogs.
4. Only then: broader web search.

## Capture the result

When external documentation was needed, create a reference immediately after the research:

```
harness new api-reference "<Technology> — <endpoint or capability>"
harness new library-reference "<Library> — <topic>"
harness new cli-reference "<Tool> — <commands>"
```

Fill in: technology, version, `source` URL, `source_authority` (official/vendor/community), `verified` date, purpose, parameters, sanitised request/response shape, a minimal usage example that matches what the project needs, known limitations, `related_implementations` and `related_tasks`.

Label every statement: `[verified: source]`, `[observed: project]`, `[inferred]`, `[unverified]`.

## Rules

- Never claim a source was reviewed if it was not accessed.
- Never store tokens, cookies, session IDs, real user data, private hostnames or sensitive response bodies. Put raw captures in `.local/` and reference them by file name.
- Paraphrase; respect licenses. Keep original links. Do not mirror documentation sites.
- Mark a reference `status: needs-revalidation` when a call fails unexpectedly, the version changes, or the source has moved. Do not re-fetch unchanged sources.
- Prefer the smallest accurate example demonstrating the behaviour the project relies on.
