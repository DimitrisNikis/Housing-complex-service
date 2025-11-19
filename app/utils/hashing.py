"""Утилиты для хэширования."""
import hashlib


def calculate_data_hash(name: str, address: str = None, description: str = None, developer: str = None) -> str:
    """Вычислить хэш значимых полей ЖК."""
    data_str = f"{name}|{address or ''}|{description or ''}|{developer or ''}"
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

