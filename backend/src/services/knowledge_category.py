from __future__ import annotations

OPS_MANUAL = "ops_manual"
MECHANISM_SPEC = "mechanism_spec"
DECISION_RECORD = "decision_record"

ALL_KNOWLEDGE_CATEGORIES = (OPS_MANUAL, MECHANISM_SPEC, DECISION_RECORD)

_DECISION_KEYWORDS = (
    "决策",
    "决定",
    "取舍",
    "路线",
    "结论",
    "decision",
    "decide",
    "tradeoff",
    "trade-off",
)

_OPS_KEYWORDS = (
    "排障",
    "命令",
    "sop",
    "步骤",
    "执行",
    "runbook",
    "playbook",
    "checklist",
    "操作手册",
)


def infer_knowledge_category(title: str, body: str) -> str:
    text = f"{title}\n{body}".lower()
    if any(keyword in text for keyword in _DECISION_KEYWORDS):
        return DECISION_RECORD
    if any(keyword in text for keyword in _OPS_KEYWORDS):
        return OPS_MANUAL
    return MECHANISM_SPEC

