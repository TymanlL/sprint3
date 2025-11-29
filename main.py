#!/usr/bin/env python3
"""EasySQL - AI-powered text-to-SQL CLI tool."""

import os
import sys
import warnings
import urllib3

# Suppress SSL warnings for GigaChat (uses self-signed certificates)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.db import DatabaseConnector, SchemaExtractor
from src.context import ContextManager
from src.llm import SQLGenerator

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="easysql")
def cli():
    """EasySQL - Query databases using natural language.

    AI-powered text-to-SQL tool with GigaChat support.
    """
    pass


@cli.command()
@click.argument("connection_string")
@click.option("--name", "-n", help="Friendly name for this database")
@click.option("--schema", "-s", default=None, help="Schema name (default: public for PostgreSQL)")
def connect(connection_string: str, name: str, schema: str):
    """Connect to database and extract schema.

    CONNECTION_STRING: Database URL (e.g., postgresql://user:pass@host:5432/db)
    """
    console.print("\n[bold blue]EasySQL[/bold blue] - Connecting to database...\n")

    try:
        # Connect to database
        with console.status("[bold green]Connecting..."):
            connector = DatabaseConnector(connection_string)
            connector.connect()
            info = connector.test_connection()

        console.print(f"[green]Connected![/green] {info['db_type']} - {info['version'][:50]}...")

        # Extract schema
        with console.status("[bold green]Extracting schema..."):
            extractor = SchemaExtractor(connector)
            db_schema = extractor.extract_full_schema(schema)

        tables_count = len(db_schema.get("tables", []))
        views_count = len(db_schema.get("views", []))

        console.print(f"[green]Schema extracted![/green] Found {tables_count} tables, {views_count} views")

        # Save context
        with console.status("[bold green]Saving context..."):
            context_manager = ContextManager()
            filepath = context_manager.save_schema(db_schema, connection_string, name)

        console.print(f"[green]Context saved![/green] {filepath}")
        console.print(f"\n[bold]Context ID:[/bold] {context_manager.current_context['id']}")

        # Show tables summary
        table = Table(title="Tables")
        table.add_column("Table", style="cyan")
        table.add_column("Columns", justify="right")
        table.add_column("Est. Rows", justify="right")

        for t in db_schema.get("tables", [])[:10]:
            table.add_row(
                t["name"],
                str(len(t.get("columns", []))),
                str(t.get("estimated_row_count", "?"))
            )

        if tables_count > 10:
            table.add_row("...", f"+{tables_count - 10} more", "")

        console.print(table)

        console.print(f"\n[bold green]Ready![/bold green] Run [cyan]easysql chat {context_manager.current_context['id']}[/cyan] to start querying")

        connector.disconnect()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command("list")
def list_schemas():
    """List saved database schemas."""
    context_manager = ContextManager()
    schemas = context_manager.list_schemas()

    if not schemas:
        console.print("[yellow]No saved schemas found.[/yellow]")
        console.print("Use [cyan]easysql connect <connection_string>[/cyan] to add one.")
        return

    table = Table(title="Saved Schemas")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Tables", justify="right")
    table.add_column("Created")

    for s in schemas:
        table.add_row(
            s["id"],
            s["name"] or "-",
            s["database_type"],
            str(s["tables_count"]),
            s["created_at"][:19] if s["created_at"] else "-"
        )

    console.print(table)


@cli.command()
@click.argument("context_id")
@click.option("--provider", "-p", default="gigachat", help="LLM provider (gigachat, openai)")
@click.option("--execute/--no-execute", "-e/-ne", default=False, help="Execute queries automatically")
@click.option("--db-url", envvar="DATABASE_URL", help="Database URL for query execution")
def chat(context_id: str, provider: str, execute: bool, db_url: str):
    """Start interactive chat session with database.

    CONTEXT_ID: Schema context ID from 'easysql list'
    """
    # Load context
    context_manager = ContextManager()
    try:
        context = context_manager.load_schema(context_id)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Schema '{context_id}' not found. Run [cyan]easysql list[/cyan] to see available schemas.")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold blue]EasySQL Chat[/bold blue]\n\n"
        f"Database: [cyan]{context.get('name', context_id)}[/cyan]\n"
        f"Type: [cyan]{context.get('database_type', 'unknown')}[/cyan]\n"
        f"Tables: [cyan]{len(context.get('schema', {}).get('tables', []))}[/cyan]\n"
        f"Provider: [cyan]{provider}[/cyan]\n\n"
        f"[dim]Commands: /quit, /tables, /history, /explain, /execute[/dim]",
        title="Session Started"
    ))

    # Initialize SQL generator
    try:
        generator = SQLGenerator(provider=provider)
        schema_text = context_manager.get_schema_for_llm()
        db_type = context.get("database_type", "postgresql")
        generator.set_context(schema_text, db_type)
    except Exception as e:
        console.print(f"[red]Error initializing LLM:[/red] {e}")
        sys.exit(1)

    # Database connector for execution
    db_connector = None
    if execute and db_url:
        try:
            db_connector = DatabaseConnector(db_url)
            db_connector.connect()
            console.print("[green]Database connected for query execution[/green]\n")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not connect to database: {e}")
            console.print("Queries will be generated but not executed.\n")

    last_sql = None

    # Main chat loop
    while True:
        try:
            question = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if not question.strip():
                continue

            # Handle commands
            if question.startswith("/"):
                cmd = question.lower().strip()

                if cmd in ("/quit", "/exit", "/q"):
                    console.print("[dim]Goodbye![/dim]")
                    break

                elif cmd == "/tables":
                    tables = context_manager.get_tables_list()
                    console.print(f"[cyan]Tables:[/cyan] {', '.join(tables)}")
                    continue

                elif cmd == "/history":
                    history = generator.get_history()
                    if not history:
                        console.print("[dim]No queries yet[/dim]")
                    else:
                        for i, h in enumerate(history[-5:], 1):
                            console.print(f"[dim]{i}.[/dim] {h['question'][:50]}...")
                    continue

                elif cmd == "/explain" and last_sql:
                    with console.status("[bold green]Analyzing..."):
                        explanation = generator.explain_sql(last_sql)
                    console.print(Panel(explanation, title="Explanation"))
                    continue

                elif cmd.startswith("/execute") and last_sql and db_connector:
                    try:
                        with console.status("[bold green]Executing..."):
                            results = db_connector.execute_query(last_sql)
                        _display_results(results)
                    except Exception as e:
                        console.print(f"[red]Execution error:[/red] {e}")
                    continue

                else:
                    console.print("[yellow]Unknown command.[/yellow] Available: /quit, /tables, /history, /explain, /execute")
                    continue

            # Generate SQL
            with console.status("[bold green]Generating SQL..."):
                result = generator.generate_sql(question)

            sql = result["sql"]
            last_sql = sql

            # Display SQL
            console.print()
            syntax = Syntax(sql, "sql", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="Generated SQL", border_style="green" if result["is_safe"] else "red"))

            if not result["is_safe"]:
                console.print("[yellow]Warning:[/yellow] This query modifies data!")

            # Execute if enabled
            if execute and db_connector and result["is_safe"]:
                if Confirm.ask("Execute this query?", default=True):
                    try:
                        with console.status("[bold green]Executing..."):
                            results = db_connector.execute_query(sql)
                        _display_results(results)
                    except Exception as e:
                        console.print(f"[red]Execution error:[/red] {e}")

                        # Offer to fix
                        if Confirm.ask("Try to fix the query?", default=True):
                            with console.status("[bold green]Fixing..."):
                                fix_result = generator.fix_sql(sql, str(e))

                            fixed_sql = fix_result["fixed_sql"]
                            syntax = Syntax(fixed_sql, "sql", theme="monokai", line_numbers=True)
                            console.print(Panel(syntax, title="Fixed SQL", border_style="blue"))

                            if Confirm.ask("Execute fixed query?", default=True):
                                try:
                                    results = db_connector.execute_query(fixed_sql)
                                    _display_results(results)
                                    last_sql = fixed_sql
                                except Exception as e2:
                                    console.print(f"[red]Still failing:[/red] {e2}")

        except KeyboardInterrupt:
            console.print("\n[dim]Use /quit to exit[/dim]")
            continue
        except EOFError:
            break

    # Cleanup
    if db_connector:
        db_connector.disconnect()


def _display_results(results: list[dict]):
    """Display query results as a table."""
    if not results:
        console.print("[dim]No results[/dim]")
        return

    # Check for affected rows (INSERT/UPDATE/DELETE)
    if len(results) == 1 and "affected_rows" in results[0]:
        console.print(f"[green]Affected rows:[/green] {results[0]['affected_rows']}")
        return

    # Create table
    table = Table(show_header=True, header_style="bold cyan")

    # Add columns
    columns = list(results[0].keys())
    for col in columns:
        table.add_column(col)

    # Add rows (limit to 50)
    for row in results[:50]:
        table.add_row(*[str(v)[:100] if v is not None else "NULL" for v in row.values()])

    console.print(table)

    if len(results) > 50:
        console.print(f"[dim]... and {len(results) - 50} more rows[/dim]")
    else:
        console.print(f"[dim]{len(results)} rows[/dim]")


@cli.command()
@click.argument("context_id")
def delete(context_id: str):
    """Delete saved schema."""
    context_manager = ContextManager()

    if context_manager.delete_schema(context_id):
        console.print(f"[green]Deleted:[/green] {context_id}")
    else:
        console.print(f"[red]Not found:[/red] {context_id}")


@cli.command()
@click.argument("context_id")
def schema(context_id: str):
    """Show schema details for a saved context."""
    context_manager = ContextManager()

    try:
        context = context_manager.load_schema(context_id)
    except FileNotFoundError:
        console.print(f"[red]Not found:[/red] {context_id}")
        sys.exit(1)

    schema_data = context.get("schema", {})

    console.print(Panel.fit(
        f"[bold]Name:[/bold] {context.get('name', '-')}\n"
        f"[bold]Type:[/bold] {schema_data.get('database_type', '-')}\n"
        f"[bold]Schema:[/bold] {schema_data.get('schema_name', '-')}\n"
        f"[bold]Created:[/bold] {context.get('created_at', '-')[:19]}",
        title=f"Context: {context_id}"
    ))

    # Tables
    for t in schema_data.get("tables", []):
        table = Table(title=f"Table: {t['name']}", show_header=True)
        table.add_column("Column", style="cyan")
        table.add_column("Type")
        table.add_column("Nullable")
        table.add_column("PK")

        for col in t.get("columns", []):
            table.add_row(
                col["name"],
                col["type"],
                "YES" if col.get("nullable") else "NO",
                "*" if col.get("is_primary_key") else ""
            )

        console.print(table)
        console.print()


if __name__ == "__main__":
    cli()
