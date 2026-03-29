import json
from pathlib import Path
from typing import Dict, Optional
from ..models.schemas import ArticleMetadata
from ..models.config import ConverterConfig
from ..writers.file_writer import FileWriter
import logging

class JSONWriter:
    def __init__(self, config: ConverterConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.file_writer = FileWriter(config, self.logger)

    def save_metadata(self, metadata: ArticleMetadata, output_dir: Path) -> Optional[Path]:
        """Сохранение метаданных в JSON файл"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Получаем имя файла из метаданных
            json_filename = metadata.source.json_filename
            if not json_filename:
                json_filename = f"{metadata.article.get('title', 'unknown')}.json"

            filepath = output_dir / json_filename

            # ИСПРАВЛЕНИЕ: Используем model_dump(mode='json') - это автоматически
            # конвертирует все Enum в их значения и готовит данные для JSON
            data_to_serialize = metadata.model_dump(mode='json', exclude_none=True)

            # Сериализация со стандартным JSONEncoder
            json_data = json.dumps(data_to_serialize, indent=2, ensure_ascii=False)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_data)

            self.logger.debug(f"Saved metadata: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save metadata to JSON: {e}")
            return None
    
    def save_all_metadata(self, metadata_store: Dict[str, ArticleMetadata], output_dir: Path):
        """Сохранение всех метаданных"""
        for filename, metadata in metadata_store.items():
            self.save_metadata(metadata, output_dir)
    
    def _clean_filename(self, filename: str) -> str:
        """Очистка имени файла"""
        import re
        clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        if len(clean_name) > 128:
            clean_name = clean_name[:128]
        return clean_name