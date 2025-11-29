"""Database schema extraction module."""

from typing import Any, Optional
from sqlalchemy import text
from .connector import DatabaseConnector


class SchemaExtractor:
    """Extract database schema information."""

    def __init__(self, connector: DatabaseConnector):
        """
        Initialize schema extractor.

        Args:
            connector: Connected DatabaseConnector instance.
        """
        self.connector = connector

    def extract_full_schema(self, schema_name: Optional[str] = None) -> dict[str, Any]:
        """
        Extract complete database schema.

        Args:
            schema_name: Specific schema to extract (default: public for PostgreSQL, database for MySQL).

        Returns:
            Dictionary with complete schema information.
        """
        if self.connector.db_type == "postgresql":
            return self._extract_postgresql_schema(schema_name or "public")
        else:
            return self._extract_mysql_schema(schema_name)

    def _extract_postgresql_schema(self, schema_name: str) -> dict[str, Any]:
        """Extract PostgreSQL schema."""
        schema = {
            "database_type": "postgresql",
            "schema_name": schema_name,
            "tables": [],
            "views": [],
            "relationships": []
        }

        # Get tables
        tables_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """

        with self.connector.engine.connect() as conn:
            tables = conn.execute(text(tables_query), {"schema": schema_name}).fetchall()

            for (table_name,) in tables:
                table_info = self._extract_postgresql_table(conn, schema_name, table_name)
                schema["tables"].append(table_info)

            # Get views
            views_query = """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = :schema
                ORDER BY table_name
            """
            views = conn.execute(text(views_query), {"schema": schema_name}).fetchall()

            for (view_name,) in views:
                view_info = self._extract_postgresql_table(conn, schema_name, view_name, is_view=True)
                schema["views"].append(view_info)

            # Get foreign key relationships
            schema["relationships"] = self._extract_postgresql_relationships(conn, schema_name)

        return schema

    def _extract_postgresql_table(self, conn, schema_name: str, table_name: str, is_view: bool = False) -> dict[str, Any]:
        """Extract single PostgreSQL table/view information."""
        columns_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """

        columns = conn.execute(text(columns_query), {"schema": schema_name, "table": table_name}).fetchall()

        # Get primary keys
        pk_query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE i.indisprimary
            AND n.nspname = :schema
            AND c.relname = :table
        """

        primary_keys = [row[0] for row in conn.execute(text(pk_query), {"schema": schema_name, "table": table_name}).fetchall()]

        # Get indexes
        indexes_query = """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = :schema AND tablename = :table
        """

        indexes = [
            {"name": row[0], "definition": row[1]}
            for row in conn.execute(text(indexes_query), {"schema": schema_name, "table": table_name}).fetchall()
        ]

        # Get row count estimate
        count_query = """
            SELECT reltuples::bigint AS estimate
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = :schema AND c.relname = :table
        """

        row_count = conn.execute(text(count_query), {"schema": schema_name, "table": table_name}).scalar() or 0

        return {
            "name": table_name,
            "type": "view" if is_view else "table",
            "columns": [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "default": col[3],
                    "max_length": col[4],
                    "precision": col[5],
                    "is_primary_key": col[0] in primary_keys
                }
                for col in columns
            ],
            "primary_keys": primary_keys,
            "indexes": indexes,
            "estimated_row_count": row_count
        }

    def _extract_postgresql_relationships(self, conn, schema_name: str) -> list[dict[str, Any]]:
        """Extract foreign key relationships."""
        fk_query = """
            SELECT
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = :schema
        """

        relationships = conn.execute(text(fk_query), {"schema": schema_name}).fetchall()

        return [
            {
                "name": row[4],
                "source_table": row[0],
                "source_column": row[1],
                "target_table": row[2],
                "target_column": row[3]
            }
            for row in relationships
        ]

    def _extract_mysql_schema(self, schema_name: Optional[str] = None) -> dict[str, Any]:
        """Extract MySQL schema."""
        schema = {
            "database_type": "mysql",
            "schema_name": schema_name,
            "tables": [],
            "views": [],
            "relationships": []
        }

        # Get current database if not specified
        if not schema_name:
            with self.connector.engine.connect() as conn:
                schema_name = conn.execute(text("SELECT DATABASE()")).scalar()
                schema["schema_name"] = schema_name

        # Get tables
        tables_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """

        with self.connector.engine.connect() as conn:
            tables = conn.execute(text(tables_query), {"schema": schema_name}).fetchall()

            for (table_name,) in tables:
                table_info = self._extract_mysql_table(conn, schema_name, table_name)
                schema["tables"].append(table_info)

            # Get views
            views_query = """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = :schema
                ORDER BY table_name
            """
            views = conn.execute(text(views_query), {"schema": schema_name}).fetchall()

            for (view_name,) in views:
                view_info = self._extract_mysql_table(conn, schema_name, view_name, is_view=True)
                schema["views"].append(view_info)

            # Get foreign key relationships
            schema["relationships"] = self._extract_mysql_relationships(conn, schema_name)

        return schema

    def _extract_mysql_table(self, conn, schema_name: str, table_name: str, is_view: bool = False) -> dict[str, Any]:
        """Extract single MySQL table/view information."""
        columns_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                column_key
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """

        columns = conn.execute(text(columns_query), {"schema": schema_name, "table": table_name}).fetchall()

        primary_keys = [col[0] for col in columns if col[6] == "PRI"]

        # Get indexes
        indexes_query = """
            SELECT index_name, column_name, non_unique
            FROM information_schema.statistics
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY index_name, seq_in_index
        """

        indexes_raw = conn.execute(text(indexes_query), {"schema": schema_name, "table": table_name}).fetchall()

        # Group indexes
        indexes_dict = {}
        for idx_name, col_name, non_unique in indexes_raw:
            if idx_name not in indexes_dict:
                indexes_dict[idx_name] = {"name": idx_name, "columns": [], "unique": not non_unique}
            indexes_dict[idx_name]["columns"].append(col_name)

        # Get row count
        count_query = """
            SELECT table_rows
            FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """

        row_count = conn.execute(text(count_query), {"schema": schema_name, "table": table_name}).scalar() or 0

        return {
            "name": table_name,
            "type": "view" if is_view else "table",
            "columns": [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES",
                    "default": col[3],
                    "max_length": col[4],
                    "precision": col[5],
                    "is_primary_key": col[6] == "PRI"
                }
                for col in columns
            ],
            "primary_keys": primary_keys,
            "indexes": list(indexes_dict.values()),
            "estimated_row_count": row_count
        }

    def _extract_mysql_relationships(self, conn, schema_name: str) -> list[dict[str, Any]]:
        """Extract MySQL foreign key relationships."""
        fk_query = """
            SELECT
                table_name AS source_table,
                column_name AS source_column,
                referenced_table_name AS target_table,
                referenced_column_name AS target_column,
                constraint_name
            FROM information_schema.key_column_usage
            WHERE table_schema = :schema
            AND referenced_table_name IS NOT NULL
        """

        relationships = conn.execute(text(fk_query), {"schema": schema_name}).fetchall()

        return [
            {
                "name": row[4],
                "source_table": row[0],
                "source_column": row[1],
                "target_table": row[2],
                "target_column": row[3]
            }
            for row in relationships
        ]

    def get_tables_summary(self) -> list[dict[str, Any]]:
        """Get quick summary of all tables."""
        if self.connector.db_type == "postgresql":
            query = """
                SELECT
                    t.table_name,
                    pg_class.reltuples::bigint as row_count,
                    COUNT(c.column_name) as column_count
                FROM information_schema.tables t
                JOIN pg_class ON pg_class.relname = t.table_name
                JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                LEFT JOIN information_schema.columns c ON c.table_name = t.table_name AND c.table_schema = t.table_schema
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                AND pg_namespace.nspname = 'public'
                GROUP BY t.table_name, pg_class.reltuples
                ORDER BY t.table_name
            """
        else:
            query = """
                SELECT
                    t.table_name,
                    t.table_rows as row_count,
                    COUNT(c.column_name) as column_count
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c ON c.table_name = t.table_name AND c.table_schema = t.table_schema
                WHERE t.table_schema = DATABASE() AND t.table_type = 'BASE TABLE'
                GROUP BY t.table_name, t.table_rows
                ORDER BY t.table_name
            """

        with self.connector.engine.connect() as conn:
            results = conn.execute(text(query)).fetchall()

        return [
            {"table": row[0], "rows": row[1], "columns": row[2]}
            for row in results
        ]
