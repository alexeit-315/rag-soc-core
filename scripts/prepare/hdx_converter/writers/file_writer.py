# writers/file_writer.py
import logging
from pathlib import Path
from typing import Optional
import shutil
from ..utils.naming_utils import NamingUtils

class FileWriter:
    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.naming_utils = NamingUtils(config)
    
    def save_file(self, content: str, base_filename: str, extension: str, 
                  output_dir: Path, title: str = "") -> Optional[Path]:
        """Сохранение файла с разрешением конфликтов имен"""
        try:
            # Создаем директорию если не существует
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{base_filename}.{extension}"
            filepath = output_dir / filename
            
            self.logger.debug(f"Attempting to save file: {filepath}")
            
            # Разрешение конфликтов имен (если метод существует)
            if hasattr(self.naming_utils, 'resolve_filename_conflict'):
                filepath = self.naming_utils.resolve_filename_conflict(filepath)
            
            # Сохранение файла
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.debug(f"Successfully saved file: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Failed to save file {base_filename}.{extension}: {e}")
            return None
    
    def backup_html_file(self, source_file: Path, dest_filename: str, dest_dir: Path) -> bool:
        """Резервное копирование HTML файла"""
        try:
            dest_path = dest_dir / f"{dest_filename}.html"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest_path)
            self.logger.debug(f"Backed up HTML: {source_file} -> {dest_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to backup HTML {source_file}: {e}")
            return False