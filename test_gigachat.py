#!/usr/bin/env python3
"""Test GigaChat connection."""

import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from dotenv import load_dotenv
load_dotenv()

from src.llm.generator import GigaChatProvider

def test_connection():
    """Test GigaChat API connection."""
    print("Testing GigaChat connection...")
    print(f"Credentials: {os.getenv('GIGACHAT_CREDENTIALS', 'NOT SET')[:20]}...")
    print(f"Scope: {os.getenv('GIGACHAT_SCOPE', 'NOT SET')}")
    print()

    try:
        provider = GigaChatProvider()
        print("[OK] Authentication successful!")
        print(f"Access token: {provider.access_token[:30]}...")
        print()

        # Test generation
        print("Testing SQL generation...")
        response = provider.generate(
            prompt="Напиши простой SELECT запрос для получения всех пользователей",
            system_prompt="Ты SQL эксперт. Отвечай только SQL кодом."
        )
        print(f"Response:\n{response}")
        print()
        print("[OK] GigaChat is working!")

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

    return True

if __name__ == "__main__":
    test_connection()
