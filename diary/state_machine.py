"""
DiaryEntry 狀態機制

設計原則:
- 純資料 + 純函數，不依賴Django ORM 或 DB
- 可以被 unit test 完整涵蓋，執行不需要 fixture
- 是 transition 規則的 single source of truth
"""
from __future__ import annotations
from diary.models import DiaryEntry

Status = DiaryEntry.StatusChoices

LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    Status.PENDING.value: frozenset({
        Status.PROCESSING.value,
        Status.FAILED.value,
    }),
    Status.PROCESSING.value: frozenset({
        Status.COMPLETED.value,
        Status.FAILED.value,
    }),
    Status.COMPLETED.value: frozenset(),    # terminal
    Status.FAILED.value: frozenset({
        Status.PENDING.value,               # 允許 reanalyze
    }),
}


def is_legal_transition(from_status: str, to_status: str) -> bool:
    """純查表，不打 DB。"""
    return to_status in LEGAL_TRANSITIONS.get(from_status, frozenset())


class IllegalStatusTransition(Exception):

    def __init__(self, *, from_status: str, to_status: str):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"DiaryEntry 狀態機違規：不允許從 {from_status!r} 轉換至 {to_status!r}")
