"""Database connector module supporting PostgreSQL and MySQL."""

from typing import Optional, Any
from urllib.parse import urlparse
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class DatabaseConnector:
    """Universal database connector with support for PostgreSQL and MySQL."""

    def __init__(self, connection_string: str):
        """
        Initialize database connector.

        Args:
            connection_string: Database URL in format:
                postgresql://user:password@host:port/database
                mysql://user:password@host:port/database
        """
        self.connection_string = connection_string
        self.engine: Optional[Engine] = None
        self.db_type: Optional[str] = None
        self._parse_connection_string()

    def _parse_connection_string(self) -> None:
        """Parse connection string to determine database type."""
        parsed = urlparse(self.connection_string)
        scheme = parsed.scheme.lower()

        if scheme in ("postgresql", "postgres"):
            self.db_type = "postgresql"
        elif scheme == "mysql":
            self.db_type = "mysql"
        else:
            raise ValueError(f"Unsupported database type: {scheme}. Supported: postgresql, mysql")

    def connect(self) -> bool:
        """
        Establish connection to database.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.engine = create_engine(self.connection_string)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}")

    def disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            query: SQL query to execute.

        Returns:
            List of dictionaries with query results.
        """
        if not self.engine:
            raise ConnectionError("Not connected to database. Call connect() first.")

        with self.engine.connect() as conn:
            result = conn.execute(text(query))

            # For SELECT queries, return results
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]

            # For INSERT/UPDATE/DELETE, commit and return affected rows
            conn.commit()
            return [{"affected_rows": result.rowcount}]

    def test_connection(self) -> dict[str, Any]:
        """
        Test connection and return database info.

        Returns:
            Dictionary with database version and connection status.
        """
        if not self.engine:
            self.connect()

        with self.engine.connect() as conn:
            if self.db_type == "postgresql":
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
            else:  # mysql
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()

        return {
            "status": "connected",
            "db_type": self.db_type,
            "version": version
        }

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
