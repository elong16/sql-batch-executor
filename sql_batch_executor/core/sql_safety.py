import re

from sql_batch_executor.core.sql_script import SqlStatement, split_sql_script


class SqlSafetyChecker:
    DANGEROUS_KEYWORDS = (
        "ALTER",
        "CREATE",
        "DELETE",
        "DROP",
        "GRANT",
        "REVOKE",
        "TRUNCATE",
        "UPDATE",
    )

    def find_dangerous_operations(self, sql: str) -> list[str]:
        return sorted({
            operation
            for item in self.find_dangerous_statements(sql)
            for operation in item[1]
        })

    def find_dangerous_statements(self, sql: str) -> list[tuple[SqlStatement, list[str]]]:
        dangerous: list[tuple[SqlStatement, list[str]]] = []
        for statement in split_sql_script(sql):
            operations = self._find_operations(statement.text)
            if operations:
                dangerous.append((statement, operations))
        return dangerous

    def _find_operations(self, sql: str) -> list[str]:
        normalized = self._strip_comments_and_literals(sql)
        found = {
            keyword
            for keyword in self.DANGEROUS_KEYWORDS
            if re.search(rf"\b{keyword}\b", normalized, flags=re.IGNORECASE)
        }
        return sorted(found)

    def _strip_comments_and_literals(self, sql: str) -> str:
        without_comments = re.sub(r"--.*?$|#.*?$|/\*.*?\*/", " ", sql, flags=re.MULTILINE | re.DOTALL)
        return re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", " ", without_comments)
