import json
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import List
from uuid import uuid4

from sql_batch_executor.app.resources import data_path

CONFIG_FILE = "connections.json"
DEFAULT_GROUP_NAME = "默认分组"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class GroupConfig:
    id: str = ""
    name: str = DEFAULT_GROUP_NAME
    collapsed: bool = False


@dataclass
class ConnectionConfig:
    id: str = ""
    name: str = ""
    group_id: str = ""
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
        self.groups: list[GroupConfig] = []
        self.load()

    def load(self):
        if not self.config_path.exists():
            self.connections = []
            self.groups = [GroupConfig(id=new_id("grp"), name=DEFAULT_GROUP_NAME)]
            return
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self.connections = []
            self.groups = [GroupConfig(id=new_id("grp"), name=DEFAULT_GROUP_NAME)]
            return

        raw_connections = data.get("connections", []) if isinstance(data, dict) else []
        if not isinstance(raw_connections, list):
            self.connections = []
            self.groups = [GroupConfig(id=new_id("grp"), name=DEFAULT_GROUP_NAME)]
            return
        groups, group_name_to_id = self._load_groups(data)

        allowed_fields = {item.name for item in fields(ConnectionConfig)}
        connections: list[ConnectionConfig] = []
        connection_ids: set[str] = set()
        group_ids = {group.id for group in groups}
        for item in raw_connections:
            if not isinstance(item, dict):
                continue
            values = {key: item[key] for key in allowed_fields if key in item}
            try:
                legacy_group_name = str(item.get("group") or DEFAULT_GROUP_NAME).strip() or DEFAULT_GROUP_NAME
                group_id = str(values.get("group_id") or "").strip()
                if not group_id:
                    group_id = group_name_to_id.get(legacy_group_name)
                if not group_id or group_id not in group_ids:
                    group_id = new_id("grp")
                    groups.append(GroupConfig(id=group_id, name=legacy_group_name))
                    group_name_to_id[legacy_group_name] = group_id
                    group_ids.add(group_id)
                connection_id = str(values.get("id") or "").strip() or new_id("conn")
                if connection_id in connection_ids:
                    connection_id = new_id("conn")
                connection_ids.add(connection_id)
                values["id"] = connection_id
                values["port"] = int(values.get("port", 3306) or 3306)
                values["group_id"] = group_id
                connections.append(ConnectionConfig(**values))
            except (TypeError, ValueError):
                continue
        self.connections = connections
        self.groups = groups or [GroupConfig(id=new_id("grp"), name=DEFAULT_GROUP_NAME)]

    def _load_groups(self, data: dict) -> tuple[list[GroupConfig], dict[str, str]]:
        raw_groups = data.get("groups", []) if isinstance(data, dict) else []
        allowed_fields = {item.name for item in fields(GroupConfig)}
        groups: list[GroupConfig] = []
        name_to_id: dict[str, str] = {}
        if isinstance(raw_groups, list):
            for item in raw_groups:
                if isinstance(item, dict):
                    values = {key: item[key] for key in allowed_fields if key in item}
                    name = str(values.get("name") or DEFAULT_GROUP_NAME).strip() or DEFAULT_GROUP_NAME
                    group_id = str(values.get("id") or "").strip() or new_id("grp")
                    collapsed = bool(values.get("collapsed", False))
                else:
                    name = str(item or "").strip() or DEFAULT_GROUP_NAME
                    group_id = new_id("grp")
                    collapsed = False
                if group_id in {group.id for group in groups}:
                    group_id = new_id("grp")
                groups.append(GroupConfig(id=group_id, name=name, collapsed=collapsed))
                name_to_id.setdefault(name, group_id)
        return groups, name_to_id

    def save(self):
        data = {
            "groups": [asdict(group) for group in self.groups],
            "connections": [asdict(c) for c in self.connections],
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def group_by_id(self, group_id: str) -> GroupConfig | None:
        return next((group for group in self.groups if group.id == group_id), None)

    def group_name(self, group_id: str) -> str:
        group = self.group_by_id(group_id)
        return group.name if group else DEFAULT_GROUP_NAME

    def default_group_id(self) -> str:
        for group in self.groups:
            if group.name == DEFAULT_GROUP_NAME:
                return group.id
        group = GroupConfig(id=new_id("grp"), name=DEFAULT_GROUP_NAME)
        self.groups.insert(0, group)
        return group.id

    def add_group(self, name: str) -> GroupConfig | None:
        name = name.strip() or DEFAULT_GROUP_NAME
        if any(group.name == name for group in self.groups):
            return None
        group = GroupConfig(id=new_id("grp"), name=name)
        self.groups.append(group)
        self.save()
        return group

    def rename_group(self, group_id: str, new_name: str) -> bool:
        new_name = new_name.strip() or DEFAULT_GROUP_NAME
        group = self.group_by_id(group_id)
        if group is None or group.name == new_name:
            return False
        if any(item.id != group_id and item.name == new_name for item in self.groups):
            return False
        group.name = new_name
        self.save()
        return True

    def add(self, conn: ConnectionConfig):
        conn.id = conn.id or new_id("conn")
        conn.group_id = conn.group_id or self.default_group_id()
        if self.group_by_id(conn.group_id) is None:
            conn.group_id = self.default_group_id()
        self.connections.append(conn)
        self.save()

    def remove(self, index: int):
        if 0 <= index < len(self.connections):
            self.connections.pop(index)
            self.save()

    def update(self, index: int, conn: ConnectionConfig):
        if 0 <= index < len(self.connections):
            conn.id = conn.id or self.connections[index].id or new_id("conn")
            conn.group_id = conn.group_id or self.default_group_id()
            if self.group_by_id(conn.group_id) is None:
                conn.group_id = self.default_group_id()
            self.connections[index] = conn
            self.save()

    def toggle(self, index: int):
        if 0 <= index < len(self.connections):
            self.connections[index].enabled = not self.connections[index].enabled
            self.save()

    def index_for_connection_id(self, connection_id: str) -> int | None:
        for index, conn in enumerate(self.connections):
            if conn.id == connection_id:
                return index
        return None

    def set_group_collapsed(self, group_id: str, collapsed: bool):
        group = self.group_by_id(group_id)
        if group is None:
            return
        group.collapsed = collapsed
        self.save()
