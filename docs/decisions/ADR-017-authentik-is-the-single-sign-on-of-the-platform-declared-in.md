---
id: ADR-017
title: Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency
summary: Authentik on k3s signs people in to every web interface (OIDC first, forward authentication otherwise); applications and groups are blueprints in Git, people live in Authentik, each service keeps a local administrator.
type: decision
status: proposed
importance: 3
created: 2026-11-18
updated: 2026-11-18
tags: []
component: 
related: []
related_tasks: []
related_milestones: []
supersedes: []
superseded_by: []
---

<!--
Architectural decision record.
Create when: a choice between viable alternatives shapes architecture or conventions.
Status vocabulary: proposed | accepted | superseded | rejected | deprecated.
Keep it short: a reader should understand the tradeoff in under two minutes.
-->

# Authentik is the single sign-on of the platform, declared in Git, never a bootstrap dependency

## Context

What situation or constraint forced a choice?

## Decision

What was decided, stated as a fact.

## Alternatives considered

- **Option A** — why not.
- **Option B** — why not.

## Consequences

Positive, negative and follow-up obligations.
