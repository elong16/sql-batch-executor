import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import List

from sql_batch_executor.app.resources import data_path

CONFIG_FILE = "connections.json"


@dataclass
class ConnectionConfig:
    name: str = ""
    group: str = "默认分组"
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = ""
    enabled: bool = True
    last_test_ok: bool | None = None  # None = not tested yet


class ConfigManager:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path) if config_path else data_path(CONFIG_FILE)
        self.connections: List[ConnectionConfig] = []
        self.load()

    def load(self):
        if not self.config_path.exists():
            self.connections = []
            return
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self.connections = []
            return

        raw_connections = data.get("connections", []) if isinstance(data, dict) else []
        if not isinstance(raw_connections, list):
            self.connections = []
            return

        allowed_fields = {item.name for item in fields(ConnectionConfig)}
        connections: list[ConnectionConfig] = []
        for item in raw_connections:
            if not isinstance(item, dict):
                continue
            values = {key: item[key] for key in allowed_fields if key in item}
            try:
                values["port"] = int(values.get("port", 3306) or 3306)
                values["group"] = str(values.get("group") or "默认分组").strip() or "默认分组"
                connections.append(ConnectionConfig(**values))
            except (TypeError, ValueError):
                continue
        self.connections = connections

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
