import shutil
from pathlib import Path
import urllib.parse
from typing import Optional
import os

class ImageProcessor:
    def __init__(self, images_dir: Path, temp_extract_dir: Path, stats_collector=None):
        self.images_dir = images_dir
        self.temp_extract_dir = temp_extract_dir
        self.stats_collector = stats_collector  # Сохраняем переданный stats_collector
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def copy_image(self, src_path: str, source_file: Path) -> Optional[str]:
        """Копирование изображения с разрешением конфликтов имен"""
        try:
            if src_path.startswith(('http://', 'https://')):
                return None

            decoded_src = urllib.parse.unquote(src_path)

            # Поиск изображения
            img_path = self._find_image_path(decoded_src, source_file)
            if not img_path:
                return None

            # Генерация имени файла
            new_name = self._generate_unique_filename(img_path.name)

            # Копирование
            destination = self.images_dir / new_name
            shutil.copy2(img_path, destination)

            # === ИСПРАВЛЕНИЕ: Увеличиваем счетчик скопированных изображений ===
            if self.stats_collector:
                self.stats_collector.increment_stat("total_images_copied")
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===
            
            return f"images/{new_name}"
            
        except Exception as e:
            return None
    
    def _find_image_path(self, src_path: str, source_file: Path) -> Optional[Path]:
        """Поиск пути к изображению"""
        possible_paths = [
            source_file.parent / src_path,
            self.temp_extract_dir / src_path,
            self.temp_extract_dir / Path(src_path).name,
            self.temp_extract_dir / "resources" / src_path,
            self.temp_extract_dir / "resources" / Path(src_path).name,
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Рекурсивный поиск
        target_filename = Path(src_path).name
        for root, dirs, files in os.walk(self.temp_extract_dir):
            for file in files:
                if file == target_filename:
                    return Path(root) / file
        
        return None
    
    def _generate_unique_filename(self, original_name: str) -> str:
        """Генерация уникального имени файла"""
        new_name = original_name
        counter = 1
        
        while (self.images_dir / new_name).exists():
            name_parts = original_name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                new_name = f"{original_name}_{counter}"
            counter += 1
        
        return new_name