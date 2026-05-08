# SQL Batch Executor

一个基于 PyQt5 和 PyQt-Fluent-Widgets 的 MySQL 批量 SQL 执行工具。

## 功能

- 管理多个 MySQL 连接
- 批量选择目标连接并执行 SQL
- 异步测试连接和异步执行 SQL，避免界面卡顿
- 检测 `DROP`、`DELETE`、`UPDATE`、`TRUNCATE` 等危险 SQL 并二次确认
- 保存执行历史到本地 `execution_history.json`
- 自定义 Fluent 风格窗口标题栏和应用图标

## 运行

```bat
run.bat
```

或：

```bash
pip install -r requirements.txt
python main.py
```

## 配置

连接配置保存在本地 `connections.json`，该文件可能包含数据库密码，默认不会提交到 Git。
可以参考 `connections.example.json` 的结构。
