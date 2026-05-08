# SQL Batch Executor

一个基于 PyQt5 和 PyQt-Fluent-Widgets 的 MySQL 批量 SQL 执行工具。

## 功能

- 管理多个 MySQL 连接
- 批量选择目标连接并执行 SQL
- 异步测试连接和异步执行 SQL，避免界面卡顿
- 检测 `DROP`、`DELETE`、`UPDATE`、`TRUNCATE` 等危险 SQL 并二次确认
- 保存执行历史到本地 `execution_history.json`
- 自定义 Fluent 风格窗口标题栏和应用图标

## 运行源码

```bat
run.bat
```

或：

```bash
pip install -r requirements.txt
python main.py
```

## 一键编译 EXE

双击运行：

```bat
build_exe.bat
```

首次构建会自动安装运行依赖和 PyInstaller。构建完成后，EXE 位于：

```text
dist\SQL批量执行器.exe
```

修改代码后，重新双击 `build_exe.bat` 即可重新打包。

## 一键提交到 GitHub

双击运行：

```bat
git_push.bat
```

脚本会自动生成带时间的提交说明，并执行：

```bash
git add -A
git commit
git push
```

也可以在命令行传入提交说明：

```bat
git_push.bat "Update UI"
```

## 配置文件

连接配置保存到 `connections.json`，执行历史保存到 `execution_history.json`。

- 源码运行时：文件保存在项目根目录
- EXE 运行时：文件保存在 EXE 同目录

这些文件可能包含数据库信息，默认不会提交到 Git。可以参考 `connections.example.json` 的结构。
