from pathlib import Path
from typing import Optional, Dict
from ..utils.file_utils import FileUtils

class PathResolver:
    def __init__(self, temp_extract_dir: Path, html_backup_dir: Path, skip_extract: bool = False):
        self.temp_extract_dir = temp_extract_dir
        self.html_backup_dir = html_backup_dir
        self.skip_extract = skip_extract
        self.file_utils = FileUtils()
    
    def normalize_path(self, href: str, base_html_path: str) -> str:
        """Нормализация пути"""
        if not href or href.startswith(('http://', 'https://', '#', 'cmdqueryname=')):
            return href
        
        try:
            base_dir = self.temp_extract_dir if not self.skip_extract else self.html_backup_dir
            base_path = base_dir / base_html_path
            
            resolved_path = self.file_utils.resolve_relative_path(href, base_path, base_dir)
            if resolved_path:
                if self.skip_extract:
                    rel_path = resolved_path.relative_to(self.html_backup_dir)
                else:
                    rel_path = resolved_path.relative_to(self.temp_extract_dir)
                return str(rel_path).replace('\\', '/')
        
        except Exception:
            pass
        
        return href
    
    def get_base_directory(self) -> Path:
        """Получение базовой директории"""
        if self.skip_extract:
            return self.html_backup_dir
        return self.temp_extract_dir

    def resolve_html_path(self, href: str, source_file: Path) -> Optional[Path]:
        """Разрешение пути к HTML файлу"""
        if not href or href.startswith(('http://', 'https://', '#', 'cmdqueryname=')):
            return None
        
        try:
            base_dir = self.temp_extract_dir if not self.skip_extract else self.html_backup_dir
            base_path = base_dir / source_file
            
            # Используем существующий метод FileUtils
            resolved_path = self.file_utils.resolve_relative_path(href, base_path, base_dir)
            
            if resolved_path and resolved_path.exists():
                return resolved_path
            
            # Попробуем найти файл в базовой директории
            simple_path = base_dir / href
            if simple_path.exists():
                return simple_path
            
        except Exception:
            pass
        
        return None

    def resolve_html_path(self, href: str, source_file: Path) -> Optional[Path]:
        """Разрешение пути к HTML файлу"""
        # Просто используем существующий метод resolve_relative_path
        return self.resolve_relative_path(href, source_file, self.get_base_directory())