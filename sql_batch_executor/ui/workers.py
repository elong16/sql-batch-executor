from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QMutex, QMutexLocker

from sql_batch_executor.core.config_manager import ConnectionConfig
from sql_batch_executor.core.sql_script import split_sql_script
from sql_batch_executor.database.manager import DatabaseClient, StatementExecutionResult


class TestConnectionWorker(QObject):
    finished = pyqtSignal(bool, str, str)

    def __init__(self, database_client: DatabaseClient, conn: ConnectionConfig):
        super().__init__()
        self.database_client = database_client
        self.conn = conn

    @pyqtSlot()
    def run(self):
        ok, message = self.database_client.test(self.conn)
        self.finished.emit(ok, message, self.conn.id)


class SqlExecutionWorker(QObject):
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, int, object)
    statement_finished = pyqtSignal(int, object)
    connection_finished = pyqtSignal(int, object)
    finished = pyqtSignal(object)
    cancelled = pyqtSignal()

    def __init__(
        self,
        database_client: DatabaseClient,
        targets: list[ConnectionConfig],
        sql: str,
        continue_on_error: bool = False,
    ):
        super().__init__()
        self.database_client = database_client
        self.targets = targets
        self.sql = sql
        self.continue_on_error = continue_on_error
        self._cancelled = False
        self._mutex = QMutex()

    def cancel(self):
        locker = QMutexLocker(self._mutex)
        self._cancelled = True

    def is_cancelled(self) -> bool:
        locker = QMutexLocker(self._mutex)
        return self._cancelled

    @pyqtSlot()
    def run(self):
        results: list = []
        statements = split_sql_script(self.sql)
        statement_count = max(1, len(statements))
        total = len(self.targets) * statement_count
        completed = 0

        for target_index, conn in enumerate(self.targets):
            if self.is_cancelled():
                self.cancelled.emit()
                return
            conn_index = target_index + 1
            conn_name = conn.name or conn.host
            conn_completed_before = completed
            self.status_changed.emit(f"执行中 {conn_index}/{len(self.targets)}: {conn_name}")

            def on_statement_done(statement_result: StatementExecutionResult):
                nonlocal completed
                completed += 1
                self.status_changed.emit(
                    f"执行中 {conn_index}/{len(self.targets)} · "
                    f"SQL {statement_result.index}/{statement_count}: {conn_name}"
                )
                self.progress_changed.emit(completed, total, statement_result)
                self.statement_finished.emit(target_index, statement_result)

            result = self.database_client.execute(
                conn,
                self.sql,
                continue_on_error=self.continue_on_error,
                progress_callback=on_statement_done,
                cancel_callback=self.is_cancelled,
            )
            results.append(result)
            self.connection_finished.emit(target_index, result)
            if completed - conn_completed_before < statement_count:
                completed = conn_completed_before + statement_count
                self.progress_changed.emit(completed, total, result)

            if self.is_cancelled():
                self.finished.emit(results)
                return
        self.finished.emit(results)
