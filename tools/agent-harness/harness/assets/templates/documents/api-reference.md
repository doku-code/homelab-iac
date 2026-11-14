---
id: {{id}}
title: {{title_yaml}}
summary: {{summary_yaml}}
type: api-reference
status: current
importance: 3
technology: {{technology}}
version: {{version}}
source: {{source}}
source_authority: official
verified: {{created}}
created: {{created}}
updated: {{updated}}
tags: [reference, external]
related_tasks: []
related_milestones: []
related_implementations: []
---

<!--
External API reference: the subset of an external API this project actually uses.
Create when: an agent had to consult external docs to implement something.
Rules: cite the source URL; record the verification date; never store tokens, cookies,
real user data or sensitive response bodies; paraphrase, do not mirror whole pages.
Mark `status: needs-revalidation` when a validation fails or the version drifts.
Label statements: [verified: source], [observed: project], [inferred], [unverified].
-->

# {{title}}

## Purpose

Why the project needs this API surface and which implementation uses it.

## Endpoint or function

`METHOD /path` or `module.function()` — [verified: source]

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|

## Request

```http
```

## Response

```json
```

## Usage example

Minimal, sanitised example demonstrating the behaviour the project relies on.

## Known limitations

-

## Verification

| Date | Method | Result |
|------|--------|--------|
| {{created}} | read official documentation | not yet verified against a live call |
