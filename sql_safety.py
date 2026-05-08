import re


class SqlSafetyChecker:
    DANGEROUS_KEYWORDS = ("DROP", "DELETE", "UPDATE", "TRUNCATE")

    def find_dangerous_operations(self, sql: str) -> list[str]:
        normalized = self._strip_comments_and_literals(sql)
        found = {
            keyword
            for keyword in self.DANGEROUS_KEYWORDS
            if re.search(rf"\b{keyword}\b", normalized, flags=re.IGNORECASE)
        }
        return sorted(found)

    def _strip_comments_and_literals(self, sql: str) -> str:
        without_comments = re.sub(r"--.*?$|/\*.*?\*/", " ", sql, flags=re.MULTILINE | re.DOTALL)
        return re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", " ", without_comments)
