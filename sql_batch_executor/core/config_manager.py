import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List

from sql_batch_executor.app.resources import data_path

CONFIG_FILE = "connections.json"


@dataclass
class ConnectionConfig:
    name: str = ""
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = ""
    enabled: bool = True


class ConfigManager:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else data_path(CONFIG_FILE)
        self.connections: List[ConnectionConfig] = []
        self.load()

    def load(self):
        if not self.config_path.exists():
            self.connections = []
            return
        with self.config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.connections = [ConnectionConfig(**item) for item in data.get("connections", [])]

    def save(self):
        data = {"connections": [asdict(c) for c in self.connections]}
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, conn: ConnectionConfig):
        self.connections.append(conn)
        self.save()

    def remove(self, index: int):
        if 0 <= index < len(self.connections):
            self.connections.pop(index)
            self.save()

    def update(self, index: int, conn: ConnectionConfig):
        if 0 <= index < len(self.connections):
            self.connections[index] = conn
            self.save()

    def toggle(self, index: int):
        if 0 <= index < len(self.connections):
            self.connections[index].enabled = not self.connections[index].enabled
            self.save()
