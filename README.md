# EasySQL

AI-powered text-to-SQL платформа с поддержкой GigaChat для российского рынка.

## Возможности

- **Text-to-SQL**: Генерация SQL-запросов из вопросов на естественном языке (русский/английский)
- **Поддержка GigaChat**: Интеграция с GigaChat API от Сбера
- **Multi-DB**: PostgreSQL, MySQL (ClickHouse в планах)
- **Автоматическое извлечение схемы**: Подключение к БД и сохранение структуры
- **Безопасность**: Проверка запросов на опасные операции
- **CLI интерфейс**: Удобная работа через командную строку

## Быстрый старт

### 1. Установка

```bash
# Клонирование репозитория
git clone <repo-url>
cd easySQL

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка GigaChat

1. Получите credentials на [developers.sber.ru](https://developers.sber.ru/portal/products/gigachat)
2. Создайте файл `.env`:

```bash
cp .env.example .env
```

3. Добавьте ваши credentials в `.env`:

```env
GIGACHAT_CREDENTIALS=your-base64-credentials-here
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
```

### 3. Подключение к базе данных

```bash
# Подключение и извлечение схемы
python main.py connect "postgresql://user:pass@localhost:5432/mydb" --name "My Database"
```

### 4. Начало работы

```bash
# Посмотреть сохранённые схемы
python main.py list

# Начать чат с базой данных
python main.py chat <context_id>

# С автоматическим выполнением запросов
python main.py chat <context_id> --execute --db-url "postgresql://user:pass@localhost:5432/mydb"
```

## Команды CLI

| Команда | Описание |
|---------|----------|
| `connect <url>` | Подключиться к БД и извлечь схему |
| `list` | Показать сохранённые схемы |
| `chat <id>` | Начать чат-сессию |
| `schema <id>` | Показать детали схемы |
| `delete <id>` | Удалить сохранённую схему |

### Опции команды `chat`

| Опция | Описание |
|-------|----------|
| `--provider`, `-p` | LLM провайдер (gigachat, openai) |
| `--execute`, `-e` | Автоматически выполнять запросы |
| `--db-url` | URL базы данных для выполнения |

### Команды в чате

| Команда | Описание |
|---------|----------|
| `/quit` | Выйти из чата |
| `/tables` | Показать список таблиц |
| `/history` | История запросов |
| `/explain` | Объяснить последний SQL |
| `/execute` | Выполнить последний SQL |

## Примеры использования

### Генерация SQL

```
You: Покажи топ-10 пользователей по количеству заказов

┌─ Generated SQL ────────────────────────────────┐
│ SELECT u.name, COUNT(o.id) as order_count      │
│ FROM users u                                    │
│ JOIN orders o ON u.id = o.user_id              │
│ GROUP BY u.id, u.name                          │
│ ORDER BY order_count DESC                      │
│ LIMIT 10;                                      │
└────────────────────────────────────────────────┘
```

### Сложные запросы

```
You: Найди клиентов, которые не делали заказов более 30 дней

You: Покажи выручку по месяцам за 2024 год

You: Какие товары чаще всего покупают вместе?
```

## Структура проекта

```
easySQL/
├── src/
│   ├── db/
│   │   ├── connector.py    # Подключение к БД
│   │   └── schema.py       # Извлечение схемы
│   ├── llm/
│   │   └── generator.py    # Генерация SQL через LLM
│   └── context/
│       └── manager.py      # Управление контекстом
├── data/                   # Сохранённые схемы (JSON)
├── main.py                 # CLI интерфейс
├── requirements.txt
└── .env.example
```

## Поддерживаемые базы данных

| База данных | Статус | Примечания |
|-------------|--------|------------|
| PostgreSQL | ✅ Готово | Полная поддержка |
| MySQL | ✅ Готово | Полная поддержка |
| ClickHouse | 🚧 В планах | - |

## Поддерживаемые LLM

| Провайдер | Статус | Примечания |
|-----------|--------|------------|
| GigaChat | ✅ Готово | По умолчанию |
| OpenAI | ✅ Готово | GPT-4, GPT-3.5 |
| YandexGPT | 🚧 В планах | - |

## Безопасность

- Токены и пароли хранятся только в `.env` (не коммитятся в git)
- Все запросы проверяются на опасные операции (DROP, DELETE, TRUNCATE)
- Опасные запросы помечаются предупреждением
- Схема БД сохраняется локально без паролей

## Roadmap

### MVP (текущая версия)
- [x] Подключение к PostgreSQL/MySQL
- [x] Извлечение схемы БД
- [x] Генерация SQL через GigaChat
- [x] CLI интерфейс
- [x] Сохранение контекста в JSON

### v0.2
- [ ] Web-интерфейс (Streamlit)
- [ ] Визуализация результатов
- [ ] Экспорт в Excel/CSV
- [ ] История запросов с поиском

### v0.3
- [ ] DBA Copilot: анализ EXPLAIN
- [ ] Рекомендации по индексам
- [ ] ClickHouse поддержка
- [ ] YandexGPT интеграция

## Лицензия

MIT

## Контакты

Проект разрабатывается в рамках AI Data Copilot платформы.
