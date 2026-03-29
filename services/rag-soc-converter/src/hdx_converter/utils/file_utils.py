import shutil
import zipfile
from pathlib import Path
import urllib.parse
from typing import Optional, List, Tuple, Dict
import hashlib
import os  # добавил os, так как он используется в методе find_all_html_files

class FileUtils:
    @staticmethod
    def extract_zip(zip_path: Path, extract_to: Path) -> Path:
        """Извлечение ZIP архива"""
        try:
            extract_to.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            return extract_to
        except Exception as e:
            raise Exception(f"Failed to extract ZIP file {zip_path}: {e}")
    
    @staticmethod
    def find_all_html_files(directory: Path, max_files: Optional[int] = None) -> List[Path]:
        """Поиск всех HTML файлов в директории"""
        html_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(Path(root) / file)
                    if max_files and len(html_files) >= max_files:
                        return html_files
        return html_files
    
    @staticmethod
    def resolve_relative_path(href: str, base_path: Path, base_dir: Path) -> Optional[Path]:
        """Разрешение относительного пути"""
        if not href or href.startswith(('http://', 'https://', '#', 'cmdqueryname=')):
            return None
        
        try:
            # Очистка пути
            if href.startswith('/'):
                href = href[1:]
            
            # Пробуем разные варианты
            possible_paths = [
                base_path.parent / href,
                base_dir / href,
                base_dir / "resources" / href,
                base_dir / href.split('/')[-1] if '/' in href else base_dir / href
            ]
            
            for path in possible_paths:
                if path.exists():
                    return path.resolve()
            
            # Поиск по имени файла
            target_filename = Path(href).name
            for html_file in base_dir.rglob("*.html"):
                if html_file.name == target_filename:
                    return html_file.resolve()
                    
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Расчет хеша файла"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                chunk = f.read(8192)
                while chunk:
                    file_hash.update(chunk)
                    chunk = f.read(8192)
                return file_hash.hexdigest()
        except Exception:
            return ""
    
    @staticmethod
    def clean_temp_directory(directory: Path):
        """Очистка временной директории"""
        if directory.exists():
            shutil.rmtree(directory)
    
    @staticmethod
    def create_directory_structure(base_dir: Path, subdirs: List[str]) -> Dict[str, Path]:
        """Создание структуры директорий"""
        directories = {}
        for subdir in subdirs:
            dir_path = base_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            directories[subdir] = dir_path
        return directories