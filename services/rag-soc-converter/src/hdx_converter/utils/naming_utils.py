# utils/naming_utils.py
import re
from pathlib import Path
from typing import Tuple, Optional, Dict
from ..models.config import ConverterConfig

class NamingUtils:
    def __init__(self, config: ConverterConfig):
        self.config = config
        # Используем дефолтный паттерн если не задан в конфиге
        if hasattr(config, 'clean_filename_pattern') and config.clean_filename_pattern:
            self.clean_filename_pattern = config.clean_filename_pattern
        else:
            self.clean_filename_pattern = re.compile(r'[<>:"/\\|?*{}\[\]()!@#$%^&=+,;]')
    
    def generate_filenames(self, title: str, dc_identifier: str, 
                          original_stem: str) -> Dict[str, str]:
        """Генерация имен файлов на основе заголовка и DC.Identifier"""
        if self.config.preserve_original_names:
            base_name = original_stem
        else:
            base_name = self._sanitize_filename(title)
        
        # Добавляем DC.Identifier для уникальности
        if dc_identifier:
            base_name = f"{base_name}_{dc_identifier}"
        
        return {
            'html': f"{base_name}.html",
            'md': f"{base_name}.md",
            'json': f"{base_name}.json",
            'txt': f"{base_name}.txt"
        }
    
    def _sanitize_filename(self, filename: str) -> str:
        """Санкционирование имени файла"""
        max_name_length = self.config.max_filename_length - 120
        if filename:
            # Используем паттерн
            filename = self.clean_filename_pattern.sub('-', filename)

            # Заменяем множественные пробелы на один
            filename = re.sub(r'\s+', ' ', filename)

            # Убираем невидимые символы
            filename = filename.strip()
            
            # Удаляем множественные дефисы
            while '--' in filename:
                filename = filename.replace('--', '-')
            
            # Удаляем дефисы в начале и конце
            filename = filename.strip('-')
            
            # Ограничиваем длину
            if len(filename) > max_name_length:
                # Обрезаем до разумной длины, сохраняя последнее слово
                truncated = filename[:max_name_length]
                last_space = truncated.rfind(' ')
                if last_space > 20:  # Если есть пробел не в начале
                    filename = truncated[:last_space]
                else:
                    filename = truncated
        
        return filename if filename else "untitled"
    
    def check_filename_length(self, filename: str) -> Tuple[bool, int]:
        """Проверка длины имени файла"""
        length = len(filename)
        return length <= self.config.max_filename_length, length
    
    def generate_short_name(self, title: str, max_length: int = 50) -> str:
        """Генерация короткого имени"""
        sanitized = self._sanitize_filename(title)
        if len(sanitized) <= max_length:
            return sanitized
        
        # Обрезаем до последнего пробела перед max_length
        truncated = sanitized[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + '...'