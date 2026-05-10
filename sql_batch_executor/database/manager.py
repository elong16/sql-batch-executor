import pymysql
from dataclasses import dataclass, field
from typing import Callable, List, Protocol, Tuple

from sql_batch_executor.core.config_manager import ConnectionConfig
from sql_batch_executor.core.sql_script import SqlStatement, split_sql_script


@dataclass
class StatementExecutionResult:
    index: int
    sql: str
    start_line: int
    success: bool
    message: str
    rows_affected: int = 0
    columns: List[str] = field(default_factory=list)
    data: List[Tuple] = field(default_factory=list)
    duration_ms: float = 0


@dataclass
class ExecutionResult:
    connection_name: str
    success: bool
    message: str
    rows_affected: int = 0
    columns: List[str] = field(default_factory=list)
    data: List[Tuple] = field(default_factory=list)
    duration_ms: float = 0
    statement_results: List[StatementExecutionResult] = field(default_factory=list)
    statements_total: int = 0
    cancelled: bool = False


class DatabaseClient(Protocol):
    def test(self, config: ConnectionConfig) -> Tuple[bool, str]:
        ...

    def fetch_databases(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
    ) -> Tuple[bool, list[str] | str]:
        ...

    def execute(
        self,
        config: ConnectionConfig,
        sql: str,
        continue_on_error: bool = False,
        progress_callback: Callable[[StatementExecutionResult], None] | None = None,
        cancel_callback: Callable[[], bool] | None = None,
    ) -> ExecutionResult:
        ...


class MySqlClient:
    def test(self, config: ConnectionConfig) -> Tuple[bool, str]:
        conn = None
        try:
            conn = pymysql.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                connect_timeout=5,
            )
            return True, "连接成功"
        except Exception as e:
            return False, str(e)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def fetch_databases(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
    ) -> Tuple[bool, list[str] | str]:
        """Fetch database list from MySQL server. Returns (True, db_list) or (False, error_msg)."""
        conn = None
        cursor = None
        try:
            conn = pymysql.connect(
                host=host, port=port, user=user, password=password,
                connect_timeout=5,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            dbs = [row[0] for row in cursor.fetchall()]
            return True, dbs
        except Exception as e:
            return False, str(e)
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def execute(
        self,
        config: ConnectionConfig,
        sql: str,
        continue_on_error: bool = False,
        progress_callback: Callable[[StatementExecutionResult], None] | None = None,
        cancel_callback: Callable[[], bool] | None = None,
    ) -> ExecutionResult:
        import time
        start = time.time()
        statements = split_sql_script(sql)
        if not statements:
            return ExecutionResult(
                connection_name=config.name,
                success=False,
                message="没有可执行 SQL",
            )

        conn = None
        cursor = None
        statement_results: list[StatementExecutionResult] = []
        cancelled = False
        try:
            conn = pymysql.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                connect_timeout=10,
            )
            cursor = conn.cursor()

            for statement in statements:
                if cancel_callback and cancel_callback():
                    cancelled = True
                    break

                statement_result = self._execute_statement(cursor, conn, statement)
                statement_results.append(statement_result)
                if progress_callback:
                    progress_callback(statement_result)

                if not statement_result.success:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    if not continue_on_error:
                        break

            elapsed = (time.time() - start) * 1000
            return self._build_execution_result(
                config=config,
                statements=statements,
                statement_results=statement_results,
                duration_ms=elapsed,
                cancelled=cancelled,
            )

        except Exception as e:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            elapsed = (time.time() - start) * 1000
            if not statement_results and statements:
                statement_results.append(
                    StatementExecutionResult(
                        index=statements[0].index,
                        sql=statements[0].text,
                        start_line=statements[0].start_line,
                        success=False,
                        message=str(e),
                        duration_ms=elapsed,
                    )
                )
            return ExecutionResult(
                connection_name=config.name,
                success=False,
                message=str(e),
                rows_affected=sum(max(item.rows_affected, 0) for item in statement_results),
                duration_ms=elapsed,
                statement_results=statement_results,
                statements_total=len(statements),
            )
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def _execute_statement(self, cursor, conn, statement: SqlStatement) -> StatementExecutionResult:
        import time
        start = time.time()
        try:
            cursor.execute(statement.text)
            elapsed = (time.time() - start) * 1000
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                return StatementExecutionResult(
                    index=statement.index,
                    sql=statement.text,
                    start_line=statement.start_line,
                    success=True,
                    message=f"查询成功，返回 {len(data)} 行",
                    rows_affected=len(data),
                    columns=columns,
                    data=data,
                    duration_ms=elapsed,
                )

            affected = cursor.rowcount
            conn.commit()
            return StatementExecutionResult(
                index=statement.index,
                sql=statement.text,
                start_line=statement.start_line,
                success=True,
                message=f"执行成功，影响 {affected} 行",
                rows_affected=affected,
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return StatementExecutionResult(
                index=statement.index,
                sql=statement.text,
                start_line=statement.start_line,
                success=False,
                message=str(e),
                duration_ms=elapsed,
            )

    def _build_execution_result(
        self,
        config: ConnectionConfig,
        statements: list[SqlStatement],
        statement_results: list[StatementExecutionResult],
        duration_ms: float,
        cancelled: bool,
    ) -> ExecutionResult:
        success_count = sum(1 for item in statement_results if item.success)
        failed_count = sum(1 for item in statement_results if not item.success)
        rows_affected = sum(max(item.rows_affected, 0) for item in statement_results)
        last_result_set = next((item for item in reversed(statement_results) if item.columns), None)

        if cancelled:
            message = f"已取消，完成 {len(statement_results)}/{len(statements)} 条语句"
            success = False
        elif len(statements) == 1 and statement_results:
            message = statement_results[0].message
            success = statement_results[0].success
        elif failed_count:
            message = f"脚本执行完成，成功 {success_count}/{len(statements)} 条，失败 {failed_count} 条"
            success = False
        else:
            message = f"脚本执行成功，完成 {success_count} 条语句"
            success = True

        return ExecutionResult(
            connection_name=config.name,
            success=success,
            message=message,
            rows_affected=rows_affected,
            columns=last_result_set.columns if last_result_set else [],
            data=last_result_set.data if last_result_set else [],
            duration_ms=duration_ms,
            statement_results=statement_results,
            statements_total=len(statements),
            cancelled=cancelled,
        )


_default_client = MySqlClient()


def test_connection(config: ConnectionConfig) -> Tuple[bool, str]:
    return _default_client.test(config)


def fetch_databases(host: str, port: int, user: str, password: str) -> Tuple[bool, list[str] | str]:
    return _default_client.fetch_databases(host, port, user, password)


def execute_sql(config: ConnectionConfig, sql: str) -> ExecutionResult:
    return _default_client.execute(config, sql)
