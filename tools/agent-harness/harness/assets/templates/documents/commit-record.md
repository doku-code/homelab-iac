---
id: {{id}}
title: {{title_yaml}}
summary: {{summary_yaml}}
type: commit-record
status: derived
commit: {{commit}}
subject: {{subject}}
branch: {{branch}}
branches: {{branches}}
author: {{author}}
authored: {{authored}}
parents: {{parents}}
created: {{created}}
updated: {{updated}}
tags: [history]
related_tasks: []
related_milestones: []
related_decisions: []
---

# {{subject}}

<!-- harness:derived:start -->
## Derived facts

| Field | Value |
|-------|-------|
| Commit | `{{commit}}` |
| Short | `{{short}}` |
| Branch context | {{branch}} (observed at sync time; also on: {{branches_text}}) |
| Author | {{author}} |
| Authored | {{authored}} |
| Parents | {{parents_text}} |

### Changed files

{{files_table}}
<!-- harness:derived:end -->

<!--
Everything below is agent-authored. Fill it in only with facts you can support:
the diff shows WHAT changed; the reason and verification must come from the task,
the conversation, test output or commit message. Set status: annotated when filled,
verified when the evidence was checked against repository state.
-->

## Summary of implementation

_Not yet annotated._

## Reason for change

_Not yet annotated._

## Verification evidence

_Not verified._

## Known limitations

_None recorded._

## Related documentation

-
