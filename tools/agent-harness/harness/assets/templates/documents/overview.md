---
id: {{id}}
title: {{title_yaml}}
summary: {{summary_yaml}}
type: overview
status: current
importance: 3
created: {{created}}
updated: {{updated}}
tags: [overview]
related: []
---

<!--
Project overview: what this project is, why it exists, how it is organised.
Create exactly once per project. Keep it under one screen; link, do not inline.
-->

# {{title}}

## Purpose

{{description}}

## Scope

What the project does and deliberately does not do.

## Structure

| Path | Purpose |
|------|---------|
| `docs/` | Knowledge documents (architecture, decisions, references, guides) |
| `milestones/` | Milestones with acceptance criteria and verification evidence |
| `tasks/` | Operational tasks with evidence |
| `history/` | Implementation history derived from Git commits |

## Where to look

- Current state: `harness status`
- Knowledge map: [docs/knowledge-map.md](knowledge-map.md)
- Conventions: `AGENTS.md`
