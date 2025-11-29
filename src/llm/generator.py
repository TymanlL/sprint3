"""SQL generator using LLM providers."""

import os
import requests
import uuid
from typing import Optional
from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        """Generate response from LLM."""
        pass


class GigaChatProvider(BaseLLMProvider):
    """GigaChat API provider (Sber)."""

    AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    def __init__(
        self,
        credentials: Optional[str] = None,
        scope: str = "GIGACHAT_API_PERS",
        model: str = "GigaChat"
    ):
        """
        Initialize GigaChat provider.

        Args:
            credentials: GigaChat credentials (Authorization Data from personal cabinet).
                        Defaults to GIGACHAT_CREDENTIALS env var.
            scope: API scope - GIGACHAT_API_PERS (personal) or GIGACHAT_API_CORP (corporate).
            model: Model name (GigaChat, GigaChat-Plus, GigaChat-Pro).
        """
        self.credentials = credentials or os.getenv("GIGACHAT_CREDENTIALS")
        if not self.credentials:
            raise ValueError(
                "GigaChat credentials not provided. "
                "Set GIGACHAT_CREDENTIALS env var or pass credentials parameter."
            )

        self.scope = scope
        self.model = model
        self.access_token: Optional[str] = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Get access token from GigaChat OAuth."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {self.credentials}"
        }

        data = {"scope": self.scope}

        response = requests.post(
            self.AUTH_URL,
            headers=headers,
            data=data,
            verify=False  # GigaChat uses self-signed cert
        )

        if response.status_code != 200:
            raise ConnectionError(
                f"GigaChat authentication failed: {response.status_code} - {response.text}"
            )

        self.access_token = response.json().get("access_token")

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Generate response from GigaChat."""
        if not self.access_token:
            self._authenticate()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }

        response = requests.post(
            self.API_URL,
            headers=headers,
            json=payload,
            verify=False
        )

        if response.status_code == 401:
            # Token expired, re-authenticate
            self._authenticate()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                verify=False
            )

        if response.status_code != 200:
            raise Exception(f"GigaChat API error: {response.status_code} - {response.text}")

        result = response.json()
        return result["choices"][0]["message"]["content"]


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var).
            model: Model to use (default: gpt-4o-mini for cost efficiency).
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY env var or pass api_key.")

        self.model = model

        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Generate response from OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )

        return response.choices[0].message.content or ""


class SQLGenerator:
    """Generate SQL queries from natural language using LLM."""

    SYSTEM_PROMPT = """Ты — эксперт по SQL. Твоя задача — преобразовывать вопросы на естественном языке в SQL-запросы.

ВАЖНЫЕ ПРАВИЛА:
1. Генерируй ТОЛЬКО SQL-запрос, без объяснений до или после
2. Используй точные имена таблиц и колонок из предоставленной схемы
3. Всегда используй правильный синтаксис SQL для указанного типа базы данных
4. При неоднозначных запросах делай разумные предположения
5. Используй подходящие JOIN когда нужны данные из нескольких таблиц
6. Добавляй LIMIT для потенциально больших результатов, если не просят все данные
7. Используй алиасы для читаемости в сложных запросах
8. НИКОГДА не используй DROP, DELETE, TRUNCATE, UPDATE или INSERT без явной просьбы
9. При сомнениях предпочитай SELECT запросы (только чтение)

Если не можешь сгенерировать валидный SQL-запрос, ответь:
-- ERROR: [объяснение почему запрос не может быть сгенерирован]

Схема базы данных:
{schema}
"""

    def __init__(self, provider: str = "gigachat", **kwargs):
        """
        Initialize SQL generator.

        Args:
            provider: LLM provider name (gigachat, openai).
            **kwargs: Additional arguments for the provider.
        """
        self.provider_name = provider.lower()
        self.provider = self._init_provider(provider, **kwargs)
        self.schema_context: Optional[str] = None
        self.db_type: Optional[str] = None
        self.history: list[dict] = []

    def _init_provider(self, provider: str, **kwargs) -> BaseLLMProvider:
        """Initialize LLM provider."""
        provider = provider.lower()

        if provider == "gigachat":
            return GigaChatProvider(**kwargs)
        elif provider == "openai":
            return OpenAIProvider(**kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}. Supported: gigachat, openai")

    def set_context(self, schema_text: str, db_type: str = "postgresql") -> None:
        """
        Set database schema context for SQL generation.

        Args:
            schema_text: Formatted schema text from ContextManager.
            db_type: Database type (postgresql, mysql).
        """
        self.schema_context = schema_text
        self.db_type = db_type

    def generate_sql(self, question: str) -> dict:
        """
        Generate SQL query from natural language question.

        Args:
            question: Natural language question about the data.

        Returns:
            Dictionary with:
                - sql: Generated SQL query
                - is_safe: Whether the query is read-only
        """
        if not self.schema_context:
            raise ValueError("No schema context set. Use set_context() first.")

        system_prompt = self.SYSTEM_PROMPT.format(schema=self.schema_context)

        user_prompt = f"""Тип базы данных: {self.db_type}

Вопрос: {question}

SQL-запрос:"""

        response = self.provider.generate(user_prompt, system_prompt)

        # Parse response
        sql = self._extract_sql(response)
        is_safe = self._check_safety(sql)

        result = {
            "sql": sql,
            "raw_response": response,
            "is_safe": is_safe,
            "question": question
        }

        self.history.append(result)

        return result

    def _extract_sql(self, response: str) -> str:
        """Extract SQL from LLM response."""
        sql = response.strip()

        # Remove markdown code blocks if present
        if sql.startswith("```sql"):
            sql = sql[6:]
        elif sql.startswith("```"):
            sql = sql[3:]

        if sql.endswith("```"):
            sql = sql[:-3]

        return sql.strip()

    def _check_safety(self, sql: str) -> bool:
        """Check if SQL query is safe (read-only)."""
        dangerous_keywords = [
            "DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT",
            "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
        ]

        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if f" {keyword} " in f" {sql_upper} " or sql_upper.startswith(f"{keyword} "):
                return False

        return True

    def explain_sql(self, sql: str) -> str:
        """
        Get explanation of SQL query in natural language.

        Args:
            sql: SQL query to explain.

        Returns:
            Natural language explanation in Russian.
        """
        system_prompt = """Ты — эксперт по SQL. Объясни данный SQL-запрос простым языком.
Будь кратким, но подробным. Упомяни:
1. Какие данные извлекаются
2. Какие таблицы задействованы
3. Какие условия/фильтры применяются
4. Как результаты сортируются/группируются

Отвечай на русском языке."""

        user_prompt = f"""Объясни этот SQL-запрос:

{sql}"""

        return self.provider.generate(user_prompt, system_prompt)

    def fix_sql(self, sql: str, error_message: str) -> dict:
        """
        Attempt to fix SQL query based on error message.

        Args:
            sql: Original SQL query that failed.
            error_message: Error message from database.

        Returns:
            Dictionary with fixed SQL.
        """
        if not self.schema_context:
            raise ValueError("No schema context set.")

        system_prompt = f"""Ты — эксперт по SQL. Исправь SQL-запрос на основе сообщения об ошибке.

Схема базы данных:
{self.schema_context}

ВАЖНО: Верни ТОЛЬКО исправленный SQL-запрос, без объяснений."""

        user_prompt = f"""Исходный запрос:
{sql}

Ошибка:
{error_message}

Исправленный запрос:"""

        response = self.provider.generate(user_prompt, system_prompt)
        fixed_sql = self._extract_sql(response)

        return {
            "original_sql": sql,
            "fixed_sql": fixed_sql,
            "error": error_message,
            "is_safe": self._check_safety(fixed_sql)
        }

    def get_history(self) -> list[dict]:
        """Get history of generated queries."""
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear query history."""
        self.history.clear()
