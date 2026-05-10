from dataclasses import dataclass


@dataclass(frozen=True)
class SqlStatement:
    index: int
    text: str
    start_line: int


def split_sql_script(sql: str) -> list[SqlStatement]:
    statements: list[SqlStatement] = []
    buffer: list[str] = []
    state: str | None = None
    line = 1
    start_line: int | None = None
    index = 1
    i = 0

    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if state == "line_comment":
            buffer.append(ch)
            if ch == "\n":
                line += 1
                state = None
            i += 1
            continue

        if state == "block_comment":
            buffer.append(ch)
            if ch == "\n":
                line += 1
            elif ch == "*" and nxt == "/":
                buffer.append(nxt)
                i += 2
                state = None
                continue
            i += 1
            continue

        if state in {"single_quote", "double_quote"}:
            quote = "'" if state == "single_quote" else '"'
            buffer.append(ch)
            if ch == "\n":
                line += 1
            elif ch == "\\" and nxt:
                buffer.append(nxt)
                if nxt == "\n":
                    line += 1
                i += 2
                continue
            elif ch == quote:
                if nxt == quote:
                    buffer.append(nxt)
                    i += 2
                    continue
                state = None
            i += 1
            continue

        if state == "backtick":
            buffer.append(ch)
            if ch == "\n":
                line += 1
            elif ch == "`":
                if nxt == "`":
                    buffer.append(nxt)
                    i += 2
                    continue
                state = None
            i += 1
            continue

        if ch == "-" and nxt == "-":
            buffer.append(ch)
            buffer.append(nxt)
            state = "line_comment"
            i += 2
            continue
        if ch == "#":
            buffer.append(ch)
            state = "line_comment"
            i += 1
            continue
        if ch == "/" and nxt == "*":
            buffer.append(ch)
            buffer.append(nxt)
            state = "block_comment"
            i += 2
            continue
        if start_line is None and not ch.isspace():
            start_line = line
        if ch == "'":
            buffer.append(ch)
            state = "single_quote"
            i += 1
            continue
        if ch == '"':
            buffer.append(ch)
            state = "double_quote"
            i += 1
            continue
        if ch == "`":
            buffer.append(ch)
            state = "backtick"
            i += 1
            continue

        if ch == ";":
            text = "".join(buffer).strip()
            if _has_executable_content(text):
                statements.append(SqlStatement(index=index, text=text, start_line=start_line or line))
                index += 1
            buffer = []
            start_line = None
            i += 1
            continue

        buffer.append(ch)
        if ch == "\n":
            line += 1
        i += 1

    text = "".join(buffer).strip()
    if _has_executable_content(text):
        statements.append(SqlStatement(index=index, text=text, start_line=start_line or line))

    return statements


def _has_executable_content(sql: str) -> bool:
    stripped = _strip_comments(sql).strip()
    return bool(stripped)


def _strip_comments(sql: str) -> str:
    output: list[str] = []
    state: str | None = None
    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if state == "line_comment":
            if ch == "\n":
                output.append(ch)
                state = None
            i += 1
            continue
        if state == "block_comment":
            if ch == "*" and nxt == "/":
                i += 2
                state = None
                continue
            i += 1
            continue
        if state in {"single_quote", "double_quote"}:
            quote = "'" if state == "single_quote" else '"'
            output.append(ch)
            if ch == "\\" and nxt:
                output.append(nxt)
                i += 2
                continue
            if ch == quote:
                if nxt == quote:
                    output.append(nxt)
                    i += 2
                    continue
                state = None
            i += 1
            continue
        if state == "backtick":
            output.append(ch)
            if ch == "`":
                if nxt == "`":
                    output.append(nxt)
                    i += 2
                    continue
                state = None
            i += 1
            continue

        if ch == "-" and nxt == "-":
            state = "line_comment"
            i += 2
            continue
        if ch == "#":
            state = "line_comment"
            i += 1
            continue
        if ch == "/" and nxt == "*":
            state = "block_comment"
            i += 2
            continue
        if ch == "'":
            state = "single_quote"
        elif ch == '"':
            state = "double_quote"
        elif ch == "`":
            state = "backtick"
        output.append(ch)
        i += 1

    return "".join(output)
