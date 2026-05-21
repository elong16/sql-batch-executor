# SqlPulse

一个基于 PyQt5 和 PyQt-Fluent-Widgets 的 MySQL 批量 SQL 执行工具，适合批量执行插入、更新等 DML 脚本。

## 功能

- 管理多个 MySQL 连接
- 批量选择目标连接并执行 SQL
- 异步测试连接和异步执行 SQL，避免界面卡顿
- 检测 `DROP`、`DELETE`、`UPDATE`、`TRUNCATE` 等危险 SQL 并二次确认
- 保存执行历史到本地 `execution_history.json`
- 自定义 Fluent 风格窗口标题栏和应用图标
- 支持切换主题色，并保存到本地偏好配置

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
dist\SqlPulse.exe
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

## 项目结构

```text
.
├── main.py                         # 源码启动入口
├── sql_batch_executor/             # 应用主包
│   ├── app/                        # 资源路径、运行目录等应用级工具
│   ├── core/                       # 配置、历史、业务服务、SQL 安全检查
│   ├── database/                   # 数据库客户端和执行结果模型
│   └── ui/                         # PyQt 界面、主题和后台线程 worker
├── assets/                         # 图标等静态资源
├── scripts/                        # 构建脚本
├── requirements.txt                # 运行依赖
└── requirements-build.txt          # 打包依赖
```

## 配置文件

连接配置保存到 `connections.json`，执行历史保存到 `execution_history.json`，界面偏好保存到 `preferences.json`。

- 源码运行时：文件保存在项目根目录
- EXE 运行时：文件保存在 EXE 同目录

这些文件可能包含数据库信息，默认不会提交到 Git。可以参考 `connections.example.json` 的结构。
