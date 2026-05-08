import pymysql
from dataclasses import dataclass, field
from typing import List, Protocol, Tuple

from sql_batch_executor.core.config_manager import ConnectionConfig


@dataclass
class ExecutionResult:
    connection_name: str
    success: bool
    message: str
    rows_affected: int = 0
    columns: List[str] = field(default_factory=list)
    data: List[Tuple] = field(default_factory=list)
    duration_ms: float = 0


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

    def execute(self, config: ConnectionConfig, sql: str) -> ExecutionResult:
        ...


class MySqlClient:
    def test(self, config: ConnectionConfig) -> Tuple[bool, str]:
        try:
            conn = pymysql.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                connect_timeout=5,
            )
            conn.close()
            return True, "连接成功"
        except Exception as e:
            return False, str(e)

    def fetch_databases(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
    ) -> Tuple[bool, list[str] | str]:
        """Fetch database list from MySQL server. Returns (True, db_list) or (False, error_msg)."""
        try:
            conn = pymysql.connect(
                host=host, port=port, user=user, password=password,
                connect_timeout=5,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            dbs = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return True, dbs
        except Exception as e:
            return False, str(e)

    def execute(self, config: ConnectionConfig, sql: str) -> ExecutionResult:
        import time
        start = time.time()
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
            cursor.execute(sql)

            elapsed = (time.time() - start) * 1000

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                result = ExecutionResult(
                    connection_name=config.name,
                    success=True,
                    message=f"查询成功，返回 {len(data)} 行",
                    rows_affected=len(data),
                    columns=columns,
                    data=data,
                    duration_ms=elapsed,
                )
            else:
                affected = cursor.rowcount
                conn.commit()
                result = ExecutionResult(
                    connection_name=config.name,
                    success=True,
                    message=f"执行成功，影响 {affected} 行",
                    rows_affected=affected,
                    duration_ms=elapsed,
                )

            cursor.close()
            conn.close()
            return result

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return ExecutionResult(
                connection_name=config.name,
                success=False,
                message=str(e),
                duration_ms=elapsed,
            )


_default_client = MySqlClient()


def test_connection(config: ConnectionConfig) -> Tuple[bool, str]:
    return _default_client.test(config)


def fetch_databases(host: str, port: int, user: str, password: str) -> Tuple[bool, list[str] | str]:
    return _default_client.fetch_databases(host, port, user, password)


def execute_sql(config: ConnectionConfig, sql: str) -> ExecutionResult:
    return _default_client.execute(config, sql)
