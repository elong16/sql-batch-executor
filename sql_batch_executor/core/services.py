from dataclasses import dataclass
from typing import Sequence

from sql_batch_executor.core.config_manager import ConfigManager, ConnectionConfig, GroupConfig
from sql_batch_executor.core.history_manager import ExecutionHistoryManager, HistoryEntry
from sql_batch_executor.core.sql_script import SqlStatement, split_sql_script
from sql_batch_executor.core.sql_safety import SqlSafetyChecker
from sql_batch_executor.database.manager import DatabaseClient, ExecutionResult, MySqlClient


@dataclass(frozen=True)
class ExecutionSummary:
    total: int
    success: int
    elapsed_ms: float
    statements_total: int = 0
    statements_success: int = 0

    @property
    def failed(self) -> int:
        return self.total - self.success

    @property
    def statements_failed(self) -> int:
        return self.statements_total - self.statements_success


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

    @property
    def groups(self) -> list[GroupConfig]:
        return self.config.groups

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

    def index_for_connection_id(self, connection_id: str) -> int | None:
        return self.config.index_for_connection_id(connection_id)

    def update_by_id(self, connection_id: str, conn: ConnectionConfig):
        index = self.index_for_connection_id(connection_id)
        if index is not None:
            self.config.update(index, conn)

    def remove_by_id(self, connection_id: str):
        index = self.index_for_connection_id(connection_id)
        if index is not None:
            self.config.remove(index)

    def toggle_by_id(self, connection_id: str):
        index = self.index_for_connection_id(connection_id)
        if index is not None:
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
        continue_on_error: bool = False,
    ) -> list[ExecutionResult]:
        return [
            self.database.execute(conn, sql, continue_on_error=continue_on_error)
            for conn in targets
        ]

    def execute_one(
        self,
        conn: ConnectionConfig,
        sql: str,
        continue_on_error: bool = False,
    ) -> ExecutionResult:
        return self.database.execute(conn, sql, continue_on_error=continue_on_error)

    def summarize(self, results: Sequence[ExecutionResult]) -> ExecutionSummary:
        statement_results = [
            statement
            for result in results
            for statement in result.statement_results
        ]
        return ExecutionSummary(
            total=len(results),
            success=sum(1 for result in results if result.success),
            elapsed_ms=sum(result.duration_ms for result in results),
            statements_total=sum(
                result.statements_total or len(result.statement_results)
                for result in results
            ),
            statements_success=sum(1 for statement in statement_results if statement.success),
        )

    def dangerous_operations(self, sql: str) -> list[str]:
        return self.safety.find_dangerous_operations(sql)

    def dangerous_statements(self, sql: str) -> list[tuple[SqlStatement, list[str]]]:
        return self.safety.find_dangerous_statements(sql)

    def split_sql(self, sql: str) -> list[SqlStatement]:
        return split_sql_script(sql)

    def record_history(self, sql: str, results: Sequence[ExecutionResult]) -> HistoryEntry:
        return self.history.append(sql, results)
