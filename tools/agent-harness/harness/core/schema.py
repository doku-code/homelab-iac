"""Document schema: types, identifiers, statuses and relationship fields.

This module is the single authoritative definition of the knowledge-document
vocabulary. Templates, validation, indexing and wiki export all import from
here rather than restating the rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Status vocabularies
# --------------------------------------------------------------------------

LIFECYCLE_STATUSES = ("planned", "active", "blocked", "completed", "cancelled")
TASK_STATUSES = ("planned", "in-progress", "blocked", "completed", "cancelled")
DECISION_STATUSES = ("proposed", "accepted", "superseded", "rejected", "deprecated", "needs-review", "archived")
# Knowledge documents: the retrieval lifecycle statuses (active, needs-review, superseded, archived) plus the
# original vocabulary, which stays valid for backward compatibility.
DOCUMENT_STATUSES = ("draft", "active", "current", "needs-review", "needs-revalidation", "deprecated", "superseded",
                     "archived")
REFERENCE_STATUSES = ("active", "current", "needs-review", "needs-revalidation", "deprecated", "superseded", "archived")
HISTORY_STATUSES = ("derived", "annotated", "verified")

PRIORITIES = ("critical", "high", "medium", "low")

# --------------------------------------------------------------------------
# Relationship fields (all optional, all lists of IDs or paths)
# --------------------------------------------------------------------------

ID_RELATION_FIELDS = (
    "related",
    "related_tasks",
    "related_milestones",
    "related_decisions",
    "depends_on",
    "supersedes",
    "superseded_by",
)
PATH_RELATION_FIELDS = ("related_implementations", "related_tests", "source_paths")
COMMIT_RELATION_FIELDS = ("related_commits",)
SCALAR_ID_FIELDS = ("milestone",)  # single-ID references

RELATION_FIELDS = ID_RELATION_FIELDS + PATH_RELATION_FIELDS + COMMIT_RELATION_FIELDS + SCALAR_ID_FIELDS

# --------------------------------------------------------------------------
# Document types
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DocType:
    name: str
    title: str
    purpose: str
    id_pattern: str
    id_prefix: str
    statuses: tuple[str, ...]
    default_dir: str
    required_fields: tuple[str, ...] = ("id", "title", "type", "status", "created", "updated")
    optional_fields: tuple[str, ...] = ()
    required_sections: tuple[str, ...] = ()
    create_when: str = ""
    numbered: bool = False  # IDs are sequential (M001, TASK-001, ADR-001)
    id_width: int = 3
    extra: dict = field(default_factory=dict)


_COMMON_OPTIONAL = ("tags", "component", "technology", "related", "related_tasks", "related_milestones",
                    "related_decisions", "related_implementations", "related_commits", "source", "version",
                    "owner", "wiki")

DOC_TYPES: dict[str, DocType] = {}


def _register(dt: DocType) -> DocType:
    DOC_TYPES[dt.name] = dt
    return dt


_register(DocType(
    name="milestone", title="Milestone", id_prefix="M", id_pattern=r"^M\d{3,}$", numbered=True,
    statuses=LIFECYCLE_STATUSES, default_dir="milestones",
    purpose="A meaningful development outcome with verifiable acceptance criteria.",
    required_fields=("id", "title", "type", "status", "priority", "created", "updated"),
    optional_fields=_COMMON_OPTIONAL + ("completion_criteria", "depends_on"),
    required_sections=("Objective", "Scope", "Expected deliverables", "Dependencies", "Acceptance criteria",
                       "Verification evidence", "Completion summary"),
    create_when="A body of work produces a user-visible outcome that should be tracked and verified as a unit.",
))
_register(DocType(
    name="task", title="Task", id_prefix="TASK-", id_pattern=r"^TASK-\d{3,}$", numbered=True,
    statuses=TASK_STATUSES, default_dir="tasks",
    purpose="An operational unit of work that guides an agent through one implementation step.",
    required_fields=("id", "title", "type", "status", "priority", "milestone", "created", "updated"),
    optional_fields=_COMMON_OPTIONAL + ("depends_on", "verification_commands", "evidence", "related_tests", "tests_justification"),
    required_sections=("Goal", "Context", "Acceptance criteria", "Verification", "Tests", "Evidence", "Completion summary"),
    create_when="Work is large enough to span a session boundary or needs explicit verification evidence.",
))
_register(DocType(
    name="decision", title="Architectural decision record", id_prefix="ADR-", id_pattern=r"^ADR-\d{3,}$",
    numbered=True, statuses=DECISION_STATUSES, default_dir="docs/decisions",
    purpose="Records a decision with a meaningful tradeoff, its context and consequences.",
    optional_fields=_COMMON_OPTIONAL + ("supersedes", "superseded_by", "deciders"),
    required_sections=("Context", "Decision", "Consequences"),
    create_when="A choice between viable alternatives shapes architecture or conventions.",
))
_register(DocType(
    name="overview", title="Project overview", id_prefix="DOC-", id_pattern=r"^[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+$",
    statuses=DOCUMENT_STATUSES, default_dir="docs",
    purpose="What the project is, why it exists, and how to navigate it.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Purpose", "Scope", "Structure", "Where to look"),
    create_when="Exactly once per project, at initialization.",
))
_register(DocType(
    name="architecture", title="Architecture", id_prefix="ARCH-", id_pattern=r"^ARCH-[A-Za-z0-9._-]+$",
    statuses=DOCUMENT_STATUSES, default_dir="docs/architecture",
    purpose="System-level or component-level structure, boundaries and data flow.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Overview", "Structure", "Key flows", "Constraints"),
    create_when="A system or component has structure that is not obvious from reading one file.",
))
_register(DocType(
    name="implementation-report", title="Implementation report", id_prefix="IMPL-",
    id_pattern=r"^IMPL-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/reports",
    purpose="Explains how a feature was implemented, why, and how it was verified.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Summary", "Changes", "Verification", "Limitations"),
    create_when="A change is large enough that a future agent would otherwise re-derive it from diffs.",
))
_register(DocType(
    name="task-report", title="Task completion report", id_prefix="REPORT-",
    id_pattern=r"^REPORT-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/reports",
    purpose="Detailed completion evidence for a task when the task file's summary is insufficient.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Outcome", "Evidence", "Remaining work"),
    create_when="A task needed more evidence or discussion than fits in its Completion summary.",
))
_register(DocType(
    name="branch-summary", title="Branch summary", id_prefix="BRANCH-",
    id_pattern=r"^BRANCH-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="history/branches",
    purpose="Agent-authored summary of what a branch set out to do and what landed.",
    optional_fields=_COMMON_OPTIONAL + ("branch",),
    required_sections=("Intent", "Outcome", "Commits of note"),
    create_when="A long-lived branch carries a coherent body of work worth summarising.",
))
_register(DocType(
    name="commit-record", title="Commit implementation record", id_prefix="HIST-",
    id_pattern=r"^HIST-[0-9a-f]{7,40}$", statuses=HISTORY_STATUSES, default_dir="history/branches",
    purpose="Derived Git facts plus agent-authored explanation for one commit.",
    required_fields=("id", "title", "type", "status", "commit", "created", "updated"),
    optional_fields=_COMMON_OPTIONAL + ("branch", "branches", "author", "authored", "parents", "subject"),
    required_sections=("Derived facts", "Summary of implementation", "Reason for change",
                       "Verification evidence", "Known limitations"),
    create_when="Generated by `harness history sync`; agents fill in the authored sections.",
))
_register(DocType(
    name="api-reference", title="External API reference", id_prefix="REF-",
    id_pattern=r"^REF-[A-Za-z0-9._-]+$", statuses=REFERENCE_STATUSES, default_dir="docs/reference/external",
    purpose="Concise local record of an external REST/GraphQL/SDK API surface the project depends on.",
    required_fields=("id", "title", "type", "status", "technology", "source", "created", "updated"),
    optional_fields=_COMMON_OPTIONAL + ("verified", "source_authority", "license"),
    required_sections=("Purpose", "Endpoint or function", "Parameters", "Request", "Response",
                       "Usage example", "Known limitations", "Verification"),
    create_when="An agent had to consult external documentation to implement something.",
))
_register(DocType(
    name="library-reference", title="Library reference", id_prefix="REF-",
    id_pattern=r"^REF-[A-Za-z0-9._-]+$", statuses=REFERENCE_STATUSES, default_dir="docs/reference/external",
    purpose="How the project uses a library or SDK: the subset that matters, with version.",
    required_fields=("id", "title", "type", "status", "technology", "source", "created", "updated"),
    optional_fields=_COMMON_OPTIONAL + ("verified", "source_authority", "license"),
    required_sections=("Purpose", "Usage in this project", "Key APIs", "Gotchas", "Verification"),
    create_when="A library's behaviour needed research beyond its obvious API.",
))
_register(DocType(
    name="cli-reference", title="CLI tool reference", id_prefix="REF-",
    id_pattern=r"^REF-[A-Za-z0-9._-]+$", statuses=REFERENCE_STATUSES, default_dir="docs/reference/external",
    purpose="Commands, flags and output formats of an external CLI the project drives.",
    required_fields=("id", "title", "type", "status", "technology", "source", "created", "updated"),
    optional_fields=_COMMON_OPTIONAL + ("verified", "source_authority", "license"),
    required_sections=("Purpose", "Commands", "Usage example", "Known limitations", "Verification"),
    create_when="An external CLI's behaviour had to be researched or observed.",
))
_register(DocType(
    name="deployment", title="Deployment procedure", id_prefix="OPS-",
    id_pattern=r"^OPS-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/operations",
    purpose="Step-by-step, verified deployment procedure for an environment.",
    optional_fields=_COMMON_OPTIONAL + ("environment",),
    required_sections=("Prerequisites", "Procedure", "Verification", "Rollback"),
    create_when="Deployment involves more than one command or any manual step.",
))
_register(DocType(
    name="troubleshooting", title="Troubleshooting procedure", id_prefix="OPS-",
    id_pattern=r"^OPS-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/operations",
    purpose="Symptom → diagnosis → fix guidance for a recurring class of problems.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Symptoms", "Diagnosis", "Resolution"),
    create_when="A problem was diagnosed once and is likely to recur.",
))
_register(DocType(
    name="known-issue", title="Known issue", id_prefix="ISSUE-",
    id_pattern=r"^ISSUE-[A-Za-z0-9._-]+$", statuses=("open", "mitigated", "resolved", "wontfix"),
    default_dir="docs/issues",
    purpose="A confirmed defect or limitation that is not yet fixed, with its workaround.",
    optional_fields=_COMMON_OPTIONAL + ("severity",),
    required_sections=("Description", "Impact", "Workaround", "Resolution plan"),
    create_when="A defect is confirmed but deliberately not fixed right now.",
))
_register(DocType(
    name="investigation", title="Investigation result", id_prefix="INV-",
    id_pattern=r"^INV-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/investigations",
    purpose="Findings from an investigation, separated into verified facts and inferences.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Question", "Method", "Findings", "Inferences", "Open questions"),
    create_when="An investigation consumed real effort and its findings would otherwise be lost.",
))
_register(DocType(
    name="failed-implementation", title="Failed implementation", id_prefix="FAIL-",
    id_pattern=r"^FAIL-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/investigations",
    purpose="Records an approach that was tried and abandoned, so it is not retried blindly.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Attempted approach", "Why it failed", "Evidence", "What to try instead"),
    create_when="An approach failed for a non-trivial reason worth remembering.",
))
_register(DocType(
    name="testing-report", title="Testing report", id_prefix="TEST-",
    id_pattern=r"^TEST-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/reports",
    purpose="Results of a test run or test campaign with exact commands and outcomes.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("Scope", "Commands", "Results", "Failures", "Not verified"),
    create_when="A test campaign backs a milestone or release decision.",
))
_register(DocType(
    name="migration", title="Migration procedure", id_prefix="OPS-",
    id_pattern=r"^OPS-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/operations",
    purpose="How to move data, schema, configuration or infrastructure from one state to another.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("From", "To", "Procedure", "Verification", "Rollback"),
    create_when="A change requires a sequenced migration that cannot be re-derived from code.",
))
_register(DocType(
    name="runbook", title="Operational runbook", id_prefix="OPS-",
    id_pattern=r"^OPS-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/operations",
    purpose="Routine operational procedure (restart, rotate, backup, scale).",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=("When to use", "Procedure", "Verification"),
    create_when="An operation is performed repeatedly and must be done the same way each time.",
))
_register(DocType(
    name="tool", title="Reusable tool documentation", id_prefix="TOOL-",
    id_pattern=r"^TOOL-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/tools",
    purpose="Usage, inputs, outputs and location of a reusable script or tool (toolbox extension point).",
    optional_fields=_COMMON_OPTIONAL + ("capabilities", "entrypoint", "language"),
    required_sections=("Purpose", "Usage", "Inputs", "Outputs", "Location"),
    create_when="A script or tool is reusable beyond the task that created it.",
))
_register(DocType(
    name="guide", title="Guide", id_prefix="GUIDE-",
    id_pattern=r"^GUIDE-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/guides",
    purpose="Human/agent-oriented how-to for a workflow in this project.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=(),
    create_when="A workflow needs explanation beyond what a skill or rule provides.",
))
_register(DocType(
    name="reference", title="Project reference", id_prefix="DOC-",
    id_pattern=r"^DOC-[A-Za-z0-9._-]+$", statuses=DOCUMENT_STATUSES, default_dir="docs/reference",
    purpose="Internal reference material (conventions, schemas, catalogs) owned by the project.",
    optional_fields=_COMMON_OPTIONAL,
    required_sections=(),
    create_when="Convention or schema information must be looked up more than once.",
))
_register(DocType(
    name="index", title="Generated index", id_prefix="INDEX-",
    id_pattern=r"^INDEX-[A-Za-z0-9._-]+$", statuses=("generated",), default_dir="docs",
    purpose="Generated navigation structure. Never edited by hand.",
    required_fields=("id", "title", "type", "status", "generated"),
    optional_fields=("tags", "generator", "source_hash"),
    required_sections=(),
    create_when="Only by harness commands.",
))

REFERENCE_TYPES = ("api-reference", "library-reference", "cli-reference")
PLANNING_TYPES = ("milestone", "task")
HISTORY_TYPES = ("commit-record", "branch-summary")

# Fields that any document may carry regardless of type.
GLOBAL_OPTIONAL_FIELDS = (
    "summary", "importance", "topics", "applies_to", "source_paths", "last_verified", "review_after",
    "tags", "component", "technology", "related", "related_tasks", "related_milestones", "related_decisions",
    "related_implementations", "related_tests", "tests_justification", "related_commits", "source", "version", "owner", "wiki", "aliases",
    "cssclasses", "generator", "source_hash", "generated",
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# --------------------------------------------------------------------------
# Retrieval lifecycle (derived from `status`; drives context retrieval, never rewrites documents)
# --------------------------------------------------------------------------

LIFECYCLE_CLASSES = ("active", "needs-review", "superseded", "archived")
_LIFECYCLE_OF_STATUS = {
    "needs-review": "needs-review", "needs-revalidation": "needs-review",
    "superseded": "superseded",
    "archived": "archived", "deprecated": "archived", "rejected": "archived", "cancelled": "archived",
    "wontfix": "archived", "resolved": "archived",
}
IMPORTANCE_RANGE = (1, 5)
DEFAULT_IMPORTANCE = 3   # missing importance: neither boosted nor penalised


def lifecycle_of(status: str | None, superseded_by: object = None) -> str:
    """Retrieval lifecycle class of a document. A non-empty `superseded_by` always means superseded."""
    if superseded_by:
        return "superseded"
    return _LIFECYCLE_OF_STATUS.get(str(status or ""), "active")
GENERIC_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-?[A-Za-z0-9._-]*$")


def doc_type(name: str) -> DocType | None:
    return DOC_TYPES.get(name)


def statuses_for(type_name: str) -> tuple[str, ...]:
    dt = DOC_TYPES.get(type_name)
    return dt.statuses if dt else DOCUMENT_STATUSES


def is_valid_id(type_name: str, doc_id: str) -> bool:
    dt = DOC_TYPES.get(type_name)
    pattern = dt.id_pattern if dt else GENERIC_ID_RE.pattern
    return re.match(pattern, str(doc_id)) is not None


def format_numbered_id(type_name: str, number: int) -> str:
    dt = DOC_TYPES[type_name]
    return f"{dt.id_prefix}{number:0{dt.id_width}d}"
