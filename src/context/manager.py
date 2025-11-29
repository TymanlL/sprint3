"""Context manager for storing and loading database schemas."""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


class ContextManager:
    """Manage database schema context storage and retrieval."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize context manager.

        Args:
            data_dir: Directory for storing schema files.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_context: Optional[dict[str, Any]] = None
        self.current_context_path: Optional[Path] = None

    def _generate_context_id(self, connection_string: str) -> str:
        """Generate unique ID for connection string."""
        # Hash connection string (without password for security)
        clean_string = self._sanitize_connection_string(connection_string)
        return hashlib.md5(clean_string.encode()).hexdigest()[:12]

    def _sanitize_connection_string(self, connection_string: str) -> str:
        """Remove password from connection string for display/storage."""
        # Simple sanitization - replace password with ***
        import re
        return re.sub(r':([^@]+)@', ':***@', connection_string)

    def save_schema(self, schema: dict[str, Any], connection_string: str, name: Optional[str] = None) -> Path:
        """
        Save database schema to JSON file.

        Args:
            schema: Schema dictionary from SchemaExtractor.
            connection_string: Original database connection string.
            name: Optional friendly name for the schema.

        Returns:
            Path to saved schema file.
        """
        context_id = self._generate_context_id(connection_string)

        context = {
            "id": context_id,
            "name": name or schema.get("schema_name", "database"),
            "connection_string_sanitized": self._sanitize_connection_string(connection_string),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "database_type": schema.get("database_type"),
            "schema": schema
        }

        filename = f"{context_id}.json"
        filepath = self.data_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(context, f, ensure_ascii=False, indent=2, default=str)

        self.current_context = context
        self.current_context_path = filepath

        return filepath

    def load_schema(self, context_id: str) -> dict[str, Any]:
        """
        Load schema from JSON file.

        Args:
            context_id: Context ID or filename.

        Returns:
            Context dictionary with schema.
        """
        # Try with and without .json extension
        filepath = self.data_dir / f"{context_id}.json"
        if not filepath.exists():
            filepath = self.data_dir / context_id

        if not filepath.exists():
            raise FileNotFoundError(f"Schema not found: {context_id}")

        with open(filepath, "r", encoding="utf-8") as f:
            context = json.load(f)

        self.current_context = context
        self.current_context_path = filepath

        return context

    def list_schemas(self) -> list[dict[str, Any]]:
        """
        List all saved schemas.

        Returns:
            List of schema summaries.
        """
        schemas = []
        for filepath in self.data_dir.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    context = json.load(f)
                    schemas.append({
                        "id": context.get("id"),
                        "name": context.get("name"),
                        "database_type": context.get("database_type"),
                        "created_at": context.get("created_at"),
                        "tables_count": len(context.get("schema", {}).get("tables", [])),
                        "filepath": str(filepath)
                    })
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(schemas, key=lambda x: x.get("created_at", ""), reverse=True)

    def delete_schema(self, context_id: str) -> bool:
        """
        Delete saved schema.

        Args:
            context_id: Context ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        filepath = self.data_dir / f"{context_id}.json"
        if filepath.exists():
            filepath.unlink()
            if self.current_context and self.current_context.get("id") == context_id:
                self.current_context = None
                self.current_context_path = None
            return True
        return False

    def get_schema_for_llm(self) -> str:
        """
        Format current schema for LLM prompt.

        Returns:
            Formatted schema string for LLM context.
        """
        if not self.current_context:
            raise ValueError("No schema loaded. Use load_schema() or save_schema() first.")

        schema = self.current_context.get("schema", {})
        db_type = schema.get("database_type", "unknown")
        schema_name = schema.get("schema_name", "")

        lines = [
            f"Database Type: {db_type}",
            f"Schema: {schema_name}",
            "",
            "=== TABLES ===",
            ""
        ]

        for table in schema.get("tables", []):
            lines.append(f"Table: {table['name']}")
            lines.append(f"  Estimated rows: {table.get('estimated_row_count', 'unknown')}")
            lines.append("  Columns:")

            for col in table.get("columns", []):
                pk_marker = " [PK]" if col.get("is_primary_key") else ""
                nullable = "NULL" if col.get("nullable") else "NOT NULL"
                lines.append(f"    - {col['name']}: {col['type']} {nullable}{pk_marker}")

            # Show relationships for this table
            relationships = [
                r for r in schema.get("relationships", [])
                if r.get("source_table") == table["name"]
            ]
            if relationships:
                lines.append("  Foreign Keys:")
                for rel in relationships:
                    lines.append(f"    - {rel['source_column']} -> {rel['target_table']}.{rel['target_column']}")

            lines.append("")

        # Views
        if schema.get("views"):
            lines.append("=== VIEWS ===")
            lines.append("")
            for view in schema.get("views", []):
                lines.append(f"View: {view['name']}")
                lines.append("  Columns:")
                for col in view.get("columns", []):
                    lines.append(f"    - {col['name']}: {col['type']}")
                lines.append("")

        return "\n".join(lines)

    def get_tables_list(self) -> list[str]:
        """Get list of table names in current context."""
        if not self.current_context:
            return []

        schema = self.current_context.get("schema", {})
        return [t["name"] for t in schema.get("tables", [])]
