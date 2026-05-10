import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence

from sql_batch_executor.app.resources import data_path
from sql_batch_executor.database.manager import ExecutionResult


HISTORY_FILE = "execution_history.json"


@dataclass(frozen=True)
class HistoryStatementItem:
    index: int
    start_line: int
    success: bool
    message: str
    rows_affected: int
    duration_ms: float


@dataclass(frozen=True)
class HistoryResultItem:
    connection_name: str
    success: bool
    message: str
    rows_affected: int
    duration_ms: float
    statements_total: int = 0
    statements: list[HistoryStatementItem] = field(default_factory=list)


@dataclass(frozen=True)
class HistoryEntry:
    executed_at: str
    sql: str
    total: int
    success: int
    failed: int
    elapsed_ms: float
    results: list[HistoryResultItem]


class ExecutionHistoryManager:
    def __init__(self, history_path: str | Path | None = None, max_entries: int = 500):
        self.history_path = Path(history_path) if history_path else data_path(HISTORY_FILE)
        self.max_entries = max_entries

    def load(self) -> list[dict]:
        if not self.history_path.exists():
            return []
        try:
            with self.history_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return []
        history = data.get("history", []) if isinstance(data, dict) else []
        return history if isinstance(history, list) else []

    def append(self, sql: str, results: Sequence[ExecutionResult]) -> HistoryEntry:
        total = len(results)
        success = sum(1 for result in results if result.success)
        entry = HistoryEntry(
            executed_at=datetime.now().isoformat(timespec="seconds"),
            sql=sql,
            total=total,
            success=success,
            failed=total - success,
            elapsed_ms=sum(result.duration_ms for result in results),
            results=[
                HistoryResultItem(
                    connection_name=result.connection_name,
                    success=result.success,
                    message=result.message,
                    rows_affected=result.rows_affected,
                    duration_ms=result.duration_ms,
                    statements_total=result.statements_total,
                    statements=[
                        HistoryStatementItem(
                            index=statement.index,
                            start_line=statement.start_line,
                            success=statement.success,
                            message=statement.message,
                            rows_affected=statement.rows_affected,
                            duration_ms=statement.duration_ms,
                        )
                        for statement in result.statement_results
                    ],
                )
                for result in results
            ],
        )

        history = self.load()
        history.append(asdict(entry))
        if len(history) > self.max_entries:
            history = history[-self.max_entries:]

        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("w", encoding="utf-8") as file:
            json.dump({"history": history}, file, ensure_ascii=False, indent=2)

        return entry
