from dataclasses import dataclass
from typing import Sequence

from sql_batch_executor.core.config_manager import ConfigManager, ConnectionConfig
from sql_batch_executor.core.history_manager import ExecutionHistoryManager, HistoryEntry
from sql_batch_executor.core.sql_safety import SqlSafetyChecker
from sql_batch_executor.database.manager import DatabaseClient, ExecutionResult, MySqlClient


@dataclass(frozen=True)
class ExecutionSummary:
    total: int
    success: int
    elapsed_ms: float

    @property
    def failed(self) -> int:
        return self.total - self.success


class ConnectionService:
    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        database_client: DatabaseClient | None = None,
        history_manager: ExecutionHistoryManager | None = None,
        safety_checker: SqlSafetyChecker | None = None,
    ):
        self.config = config_manager or ConfigManager()
        self.database = database_client or MySqlClient()
        self.history = history_manager or ExecutionHistoryManager()
        self.safety = safety_checker or SqlSafetyChecker()

    @property
    def connections(self) -> list[ConnectionConfig]:
        return self.config.connections

    def enabled_connections(self) -> list[ConnectionConfig]:
        return [conn for conn in self.connections if conn.enabled]

    def add(self, conn: ConnectionConfig):
        self.config.add(conn)

    def update(self, index: int, conn: ConnectionConfig):
        self.config.update(index, conn)

    def remove(self, index: int):
        self.config.remove(index)

    def toggle(self, index: int):
        self.config.toggle(index)

    def test(self, index: int) -> tuple[bool, str]:
        return self.database.test(self.connections[index])

    def fetch_databases(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
    ) -> tuple[bool, list[str] | str]:
        return self.database.fetch_databases(host, port, user, password)

    def resolve_targets(
        self,
        enabled_connections: Sequence[ConnectionConfig],
        selected_indices: Sequence[int],
    ) -> list[ConnectionConfig]:
        return [enabled_connections[index] for index in selected_indices]

    def execute_many(
        self,
        targets: Sequence[ConnectionConfig],
        sql: str,
    ) -> list[ExecutionResult]:
        return [self.database.execute(conn, sql) for conn in targets]

    def execute_one(self, conn: ConnectionConfig, sql: str) -> ExecutionResult:
        return self.database.execute(conn, sql)

    def summarize(self, results: Sequence[ExecutionResult]) -> ExecutionSummary:
        return ExecutionSummary(
            total=len(results),
            success=sum(1 for result in results if result.success),
            elapsed_ms=sum(result.duration_ms for result in results),
        )

    def dangerous_operations(self, sql: str) -> list[str]:
        return self.safety.find_dangerous_operations(sql)

    def record_history(self, sql: str, results: Sequence[ExecutionResult]) -> HistoryEntry:
        return self.history.append(sql, results)
