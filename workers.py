from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from config_manager import ConnectionConfig
from db_manager import DatabaseClient, ExecutionResult


class TestConnectionWorker(QObject):
    finished = pyqtSignal(bool, str, str)

    def __init__(self, database_client: DatabaseClient, conn: ConnectionConfig):
        super().__init__()
        self.database_client = database_client
        self.conn = conn

    @pyqtSlot()
    def run(self):
        ok, message = self.database_client.test(self.conn)
        self.finished.emit(ok, message, self.conn.name or self.conn.host)


class SqlExecutionWorker(QObject):
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int, int, object)
    finished = pyqtSignal(object)

    def __init__(
        self,
        database_client: DatabaseClient,
        targets: list[ConnectionConfig],
        sql: str,
    ):
        super().__init__()
        self.database_client = database_client
        self.targets = targets
        self.sql = sql

    @pyqtSlot()
    def run(self):
        results: list[ExecutionResult] = []
        total = len(self.targets)
        for index, conn in enumerate(self.targets, start=1):
            self.status_changed.emit(f"执行中 {index}/{total}: {conn.name or conn.host}")
            result = self.database_client.execute(conn, self.sql)
            results.append(result)
            self.progress_changed.emit(index, total, result)
        self.finished.emit(results)
