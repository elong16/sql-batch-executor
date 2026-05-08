import json
import os
from dataclasses import dataclass, asdict, field
from typing import List

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
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.connections: List[ConnectionConfig] = []
        self.load()

    def load(self):
        if not os.path.exists(self.config_path):
            self.connections = []
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.connections = [ConnectionConfig(**item) for item in data.get("connections", [])]

    def save(self):
        data = {"connections": [asdict(c) for c in self.connections]}
        with open(self.config_path, "w", encoding="utf-8") as f:
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
