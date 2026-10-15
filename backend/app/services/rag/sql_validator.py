from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

try:
    import sqlglot
    from sqlglot import exp
except Exception:  # pragma: no cover - dependency installed in production image
    sqlglot = None
    exp = None

from app.core.config import settings

ALLOWED_TABLES = {
    "indicator_values",
    "indicators",
    "datasets",
    "sources",
    "data_dimensions",
}

ALLOWED_COLUMNS = {
    "indicator_values": {"id", "indicator_id", "date", "value", "region", "sector", "dimension_json"},
    "indicators": {"id", "indicator_id", "name_en", "name_ar", "description_en", "description_ar", "unit", "frequency", "source_id", "dataset_id", "country", "category", "last_updated", "verification_status"},
    "datasets": {"id", "source_id", "slug", "name_en", "name_ar", "source_url", "verification_status", "last_updated"},
    "sources": {"id", "slug", "name_en", "name_ar", "organization", "url", "source_type"},
    "data_dimensions": {"id", "indicator_id", "name", "value", "metadata_json"},
}

DENIED_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke",
    "copy", "vacuum", "analyze", "attach", "detach", "pragma", "execute", "call", "do", "set",
    "reset", "listen", "notify", "load", "extension", "program", "pg_read_file", "pg_ls_dir",
}
DENIED_FRAGMENTS = {"information_schema", "pg_catalog", "pg_", "lo_import", "lo_export", "dblink", "file_fdw"}
ALLOWED_FUNCTIONS = {"avg", "sum", "min", "max", "count", "coalesce", "round", "date_part", "extract", "lower", "upper"}


@dataclass
class SQLValidationResult:
    valid: bool
    sql: str
    params: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _normalize(sql: str) -> str:
    return " ".join(sql.strip().split())


def validate_sql(sql: str, params: dict[str, Any] | None = None) -> SQLValidationResult:
    params = dict(params or {})
    sql = _normalize(sql)
    errors: list[str] = []
    lowered = sql.lower()

    if not sql:
        return SQLValidationResult(False, sql, params, ["SQL is empty"])
    if "--" in sql or "/*" in sql or "*/" in sql:
        errors.append("SQL comments are not allowed")
    if ";" in sql.rstrip(";"):
        errors.append("Multiple SQL statements are not allowed")
    sql = sql.rstrip(";").strip()
    lowered = sql.lower()
    first = lowered.split(" ", 1)[0]
    if first not in {"select", "with"}:
        errors.append("Only SELECT queries and safe CTEs are allowed")
    for keyword in DENIED_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            errors.append(f"Forbidden SQL keyword: {keyword}")
    for fragment in DENIED_FRAGMENTS:
        if fragment in lowered:
            errors.append(f"Forbidden SQL fragment: {fragment}")

    placeholders = set(re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", sql))
    missing = sorted(placeholders - set(params))
    if missing:
        errors.append("Missing SQL parameters: " + ", ".join(missing))

    if sqlglot is not None:
        try:
            tree = sqlglot.parse_one(sql, read="postgres")
            if not isinstance(tree, (exp.Select, exp.Union)) and tree.find(exp.Select) is None:
                errors.append("Query does not contain a SELECT statement")
            cte_outputs: dict[str, set[str]] = {}
            for cte in tree.find_all(exp.CTE):
                cte_name = (cte.alias_or_name or "").lower()
                if not cte_name:
                    errors.append("Unnamed CTE is not allowed")
                    continue
                outputs: set[str] = set()
                select_node = cte.this.find(exp.Select) if not isinstance(cte.this, exp.Select) else cte.this
                if select_node is not None:
                    for expression in select_node.expressions:
                        output_name = (expression.alias_or_name or "").lower()
                        if output_name:
                            outputs.add(output_name)
                cte_outputs[cte_name] = outputs

            aliases: dict[str, str] = {}
            for table in tree.find_all(exp.Table):
                name = table.name.lower()
                # A CTE reference is a derived table whose underlying SELECT is
                # validated independently below. All physical tables remain allowlisted.
                if name in cte_outputs:
                    aliases[(table.alias_or_name or name).lower()] = name
                    continue
                if name not in ALLOWED_TABLES:
                    errors.append(f"Table is not allowed: {name}")
                    continue
                aliases[name] = name
                aliases[(table.alias_or_name or name).lower()] = name

            allowed_unqualified = set().union(*ALLOWED_COLUMNS.values())
            selected_aliases = {
                (expression.alias_or_name or "").lower()
                for select_node in tree.find_all(exp.Select)
                for expression in select_node.expressions
                if expression.alias_or_name
            }
            for column in tree.find_all(exp.Column):
                column_name = column.name.lower()
                qualifier = (column.table or "").lower()
                if qualifier:
                    resolved = aliases.get(qualifier)
                    if resolved in ALLOWED_TABLES:
                        if column_name not in ALLOWED_COLUMNS[resolved]:
                            errors.append(f"Column is not allowed: {qualifier}.{column_name}")
                    elif resolved in cte_outputs:
                        if column_name not in cte_outputs[resolved]:
                            errors.append(f"CTE column is not allowed: {qualifier}.{column_name}")
                    else:
                        errors.append(f"Unknown table alias: {qualifier}")
                elif column_name not in allowed_unqualified and column_name not in selected_aliases:
                    errors.append(f"Column is not allowed: {column_name}")

            for func in tree.find_all(exp.Func):
                name = (func.sql_name() or "").lower()
                if name and name not in ALLOWED_FUNCTIONS and name not in {"cast"}:
                    errors.append(f"Function is not allowed: {name}")
            for node_type in (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Command):
                if tree.find(node_type):
                    errors.append(f"Unsafe SQL node: {node_type.__name__}")
        except Exception as exc:
            errors.append(f"SQL parser rejected the query: {type(exc).__name__}")
    else:
        # Dependency-light fallback used in minimal environments where sqlglot
        # is not installed. Keep it conservative: identify CTE names, physical
        # table aliases, and qualified columns with simple SQL token patterns.
        cte_names = set(re.findall(r"(?:^\s*with\s+|,\s*)([A-Za-z_][A-Za-z0-9_]*)\s+as\s*\(", lowered))
        aliases: dict[str, str] = {}
        for match in re.finditer(r"\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+(?:as\s+)?([A-Za-z_][A-Za-z0-9_]*))?", lowered):
            table, alias = match.group(1), match.group(2)
            # Avoid treating SQL clause keywords as aliases.
            if alias in {"where", "join", "left", "right", "inner", "outer", "full", "cross", "group", "order", "limit", "on"}:
                alias = None
            if table in cte_names:
                aliases[alias or table] = table
                continue
            if table not in ALLOWED_TABLES:
                errors.append(f"Table is not allowed: {table}")
                continue
            aliases[table] = table
            aliases[alias or table] = table

        # Validate qualified physical-table columns. CTE output columns are not
        # re-derived here; the inner SELECT's physical references are checked,
        # and selecting from the named CTE is allowed.
        for qualifier, column_name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b", lowered):
            resolved = aliases.get(qualifier)
            if resolved in ALLOWED_TABLES and column_name not in ALLOWED_COLUMNS[resolved]:
                errors.append(f"Column is not allowed: {qualifier}.{column_name}")
            elif resolved is None and qualifier not in cte_names:
                errors.append(f"Unknown table alias: {qualifier}")

    limit_match = re.search(r"\blimit\s+(?::([A-Za-z_][A-Za-z0-9_]*)|(\d+))", sql, flags=re.IGNORECASE)
    if limit_match:
        if limit_match.group(2) and int(limit_match.group(2)) > settings.sql_row_limit:
            errors.append(f"LIMIT exceeds maximum row limit of {settings.sql_row_limit}")
        if limit_match.group(1):
            key = limit_match.group(1)
            try:
                if int(params[key]) > settings.sql_row_limit:
                    errors.append(f"LIMIT exceeds maximum row limit of {settings.sql_row_limit}")
            except Exception:
                errors.append("Invalid LIMIT parameter")
    else:
        sql = f"{sql} LIMIT :__row_limit"
        params["__row_limit"] = settings.sql_row_limit

    return SQLValidationResult(not errors, sql, params, errors)
