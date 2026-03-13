import shutil
from pathlib import Path
from typing import Optional
import logging

class HTMLBackupWriter:
    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def backup_html(self, source_file: Path, base_filename: str, backup_dir: Path) -> bool:
        """Резервное копирование HTML файла"""
        try:
            # Убираем .html если уже есть в base_filename
            if base_filename.lower().endswith('.html'):
                base_filename = base_filename[:-5]

            dest_path = backup_dir / f"{base_filename}.html"
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest_path)
            return True
        except Exception as e:
            return False