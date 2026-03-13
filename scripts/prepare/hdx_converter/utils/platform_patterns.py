"""
Модуль для работы с шаблонами платформ и моделей.

Этот модуль содержит регулярные выражения для извлечения информации о платформах
и моделях из текста контента. Паттерны могут быть расширены при необходимости.

Использование:
1. Для извлечения серий продуктов используйте extract_product_series()
2. Для извлечения совместимых моделей используйте extract_compatible_models()
3. Для добавления новых паттернов обновите соответствующие списки

Пример добавления нового паттерна:
    PLATFORM_PATTERNS.append(r'NEXUS\d+[A-Z]*')  # Для оборудования Cisco Nexus
"""

import re
from typing import List, Dict, Tuple, Set

# Регулярные выражения для извлечения серий продуктов
PRODUCT_SERIES_PATTERNS = [
    r'USG\d+[A-Z]+',          # USG серии (USG6000F, USG6600F)
    r'CE\d{3,}[A-Z\d\-]{0,17}',           # CE серии (минимум 3 цифры)
    r'S\d{3,}[A-Z\d\-]{0,17}',            # S серии (минимум 3 цифры)
    r'AR\d{3,}[A-Z\d\-]{0,17}',           # AR серии (минимум 3 цифры)
    r'NetEngine\d+[A-Z]*',    # NetEngine серии
    r'Atlas\d+[A-Z]*',        # Atlas серии
    r'HiSecEngine\d+[A-Z\-]*', # HiSecEngine серии
    r'CloudEngine\d+[A-Z]*',  # CloudEngine серии
    r'AirEngine\d+[A-Z]*',    # AirEngine серии
]

# Регулярные выражения для извлечения совместимых моделей
COMPATIBLE_MODELS_PATTERNS = [
    r'USG\d+[A-Z\-]+',        # Все модели USG
    r'CE\d{3,}[A-Z\d\-]{0,17}',  # Все модели CE (минимум 3 цифры, общая длина до 20)
    r'S\d{3,}[A-Z\d\-]{0,17}',   # Все модели S серии (минимум 3 цифры, общая длина до 20)
    r'AR\d{3,}[A-Z\d\-]{0,17}',  # Все модели AR серии (минимум 3 цифры, общая длина до 20)
    r'NetEngine\s*\d+[A-Z]*', # Все модели NetEngine
    r'Atlas\s*\d+[A-Z]*',     # Все модели Atlas
    r'HiSecEngine\d+[A-Z\-]*',# Все модели HiSecEngine
    r'CloudEngine\d+[A-Z]*',  # Все модели CloudEngine
    r'AirEngine\d+[A-Z]*',    # Все модели AirEngine
]

class PlatformPatterns:
    """Класс для работы с паттернами платформ"""
    
    @staticmethod
    def extract_product_series(content: str) -> List[str]:
        """Извлечение серий продуктов из текста"""
        series = set()
        content_lower = content.lower()
        
        for pattern in PRODUCT_SERIES_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Проверяем, что это действительно серия (не модель)
                if not any(x in match.upper() for x in ['V', 'R', 'C', 'SPC']):
                    series.add(match)
        
        return list(series)
    
    @staticmethod
    def extract_compatible_models(content: str) -> List[str]:
        """Извлечение совместимых моделей из текста"""
        models = set()
        
        for pattern in COMPATIBLE_MODELS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Нормализуем модель (убираем лишние пробелы)
                model = ' '.join(match.split())
                models.add(model)
        
        return list(models)
    
    @staticmethod
    def extract_all_platforms(content: str) -> Tuple[List[str], List[str]]:
        """Извлечение всех платформ и моделей"""
        series = PlatformPatterns.extract_product_series(content)
        models = PlatformPatterns.extract_compatible_models(content)
        
        # Убираем серии из моделей, если они там есть
        clean_models = [m for m in models if m not in series]
        
        return series, clean_models
    
    @staticmethod
    def add_product_series_pattern(pattern: str):
        """Добавление нового паттерна для серий продуктов"""
        if pattern not in PRODUCT_SERIES_PATTERNS:
            PRODUCT_SERIES_PATTERNS.append(pattern)
    
    @staticmethod
    def add_compatible_model_pattern(pattern: str):
        """Добавление нового паттерна для совместимых моделей"""
        if pattern not in COMPATIBLE_MODELS_PATTERNS:
            COMPATIBLE_MODELS_PATTERNS.append(pattern)