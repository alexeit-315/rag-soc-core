from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json
from bs4 import BeautifulSoup

from ..models.schemas import (
    ArticleMetadata, SourceInfo, TechnicalMetadata, FirmwareVersions,
    Platforms, ContentFlags, Relations, RelatedArticle, Validation
)
from ..models.config import ConverterConfig
from ..parsers.navigation_parser import NavigationParser
from ..parsers.metadata_parser import MetadataParser
from ..utils.path_resolver import PathResolver
from ..utils.naming_utils import NamingUtils

class MetadataManager:
    def __init__(self, config: ConverterConfig, path_resolver: PathResolver):
        self.config = config
        self.path_resolver = path_resolver
        self.metadata_store: Dict[str, ArticleMetadata] = {}
        self.files_without_dc_identifier: List[Path] = []
        self.registered_dc_identifiers = set()
        
        # Инициализация парсеров
        self.navigation_parser = NavigationParser(path_resolver)
        self.metadata_parser = MetadataParser()
        self.naming_utils = NamingUtils(config)
    
    def create_article_metadata(self, soup: BeautifulSoup, html_file: Path, title: str, 
                               dc_identifier: str, html_filename: str, md_filename: str,
                               hdx_hash: str = "") -> ArticleMetadata:
        """Создание метаданных статьи с правильными типами для Pydantic - ИСПРАВЛЕННАЯ (пункт 18)"""
        # Извлечение базовых метаданных из HTML
        html_metadata = self.metadata_parser.extract_metadata_from_html(soup)

        # Извлечение полной иерархии
        hierarchy = self.navigation_parser.extract_full_hierarchy(soup, html_file)

        # ИСПРАВЛЕНИЕ 1: Используем html_backup_dir для относительных путей
        base_dir = self.path_resolver.html_backup_dir if self.config.skip_extract else self.path_resolver.temp_extract_dir
        html_path = str(html_file.relative_to(base_dir))

        # ИСПРАВЛЕНИЕ для пункта 18: Получаем имя HDX файла из конвертера
        # hdx_filename будет заполнен позже в converter.py при вызове этого метода
        hdx_filename = ""

        # Создание информации об источнике
        safe_title = self.naming_utils._sanitize_filename(title)
        source_info = SourceInfo(
            hdx_filename=hdx_filename,  # Будет заполнено позже
            html_filename=html_filename,
            html_path=html_path,
            extraction_date=datetime.now().isoformat(),
            json_filename = f"{safe_title}_{dc_identifier}.json",
            md_filename=md_filename,
            hdx_hash=hdx_hash
        )

        # Создание технических метаданных с правильными типами
        technical_metadata = TechnicalMetadata(
                firmware_versions=FirmwareVersions(
                    primary=str(self.config.global_firmware_versions.get("primary", "")),  # ИСПРАВЛЕНО: явное преобразование в str
                    all_versions=list(self.config.global_firmware_versions.get("all_versions", [])),  # ИСПРАВЛЕНО: явное преобразование в list
                    applicability_scope=self.config.global_firmware_versions.get("applicability_scope", "unknown"),
                    confirmed_by_user=bool(self.config.global_firmware_versions.get("confirmed_by_user", False))  # ИСПРАВЛЕНО: явное преобразование в bool
                ),
                platforms=Platforms(
                    product_series=str(self.config.global_platforms.get("product_series", "")),  # ИСПРАВЛЕНО: явное преобразование в str
                    compatible_models=list(self.config.global_platforms.get("compatible_models", [])),  # ИСПРАВЛЕНО: явное преобразование в list
                    model_limitations=dict(self.config.global_platforms.get("model_limitations", {})),  # ИСПРАВЛЕНО: явное преобразование в dict
                    applicability_scope=self.config.global_platforms.get("applicability_scope", "unknown"),
                    confirmed_by_user=bool(self.config.global_platforms.get("confirmed_by_user", False))  # ИСПРАВЛЕНО: явное преобразование в bool
                ),
                features=html_metadata.get("features", []),
                content_flags=ContentFlags(
                    contains_cli_commands=False,
                    contains_configuration_steps=False,
                    contains_tables=False,
                    contains_code_examples=False,
                    contains_warnings=False
                )
            )

        # Создание связей с правильными типами
        relations = Relations(
            parent_article=RelatedArticle(
                title="",
                dc_identifier="",
                html_filename="",
                html_path="",
                md_filename=""
            ),
            previous_article=RelatedArticle(
                title="",
                dc_identifier="",
                html_filename="",
                html_path="",
                md_filename=""
            ),
            next_article=RelatedArticle(
                title="",
                dc_identifier="",
                html_filename="",
                html_path="",
                md_filename=""
            ),
            internal_links=[],
            external_links=[]
        )

        # Создание метаданных статьи
        metadata = ArticleMetadata(
            metadata_version="1.2",
            source=source_info,
            article={
                "title": title,
                "md_filename": md_filename,
                "dc_identifier": dc_identifier,
                "document_type": html_metadata.get("document_type", ""),
                "language": html_metadata.get("language", ""),
                "hierarchy": hierarchy,
                "section_structure": [],  # Будет заполнено позже
                "dc_publisher": html_metadata.get("dc_publisher", ""),
                "dc_audience_job": html_metadata.get("dc_audience_job", ""),
                "prodname": html_metadata.get("prodname", ""),
                "version": html_metadata.get("version", ""),
                "brand": html_metadata.get("brand", ""),
                "addwebmerge": html_metadata.get("addwebmerge", "")
            },
            technical_metadata=technical_metadata,
            relations=relations,
            validation=Validation(
                is_valid=False,
                missing_fields={
                    "mandatory": [],
                    "recommended": [],
                    "optional": []
                },
                errors=[],
                warnings=[],
                info=[]
            )
        )

        return metadata
    
    def add_metadata(self, filename: str, metadata: ArticleMetadata):
        """Добавление метаданных в хранилище"""
        self.metadata_store[filename] = metadata
    
    def get_metadata_by_filename(self, filename: str) -> Optional[ArticleMetadata]:
        """Получение метаданных по имени файла"""
        return self.metadata_store.get(filename)
    
    def get_all_metadata(self) -> Dict[str, ArticleMetadata]:
        """Получение всех метаданных"""
        return self.metadata_store
    
    def register_dc_identifier(self, dc_identifier: str, html_file: Path) -> bool:
        """Регистрация DC.Identifier (проверка уникальности)"""
        if dc_identifier in self.registered_dc_identifiers:
            return False
        
        self.registered_dc_identifiers.add(dc_identifier)
        return True
    
    def add_file_without_dc_identifier(self, html_file: Path):
        """Добавление файла без DC.Identifier в список пропущенных"""
        self.files_without_dc_identifier.append(html_file)
    
    def update_content_flags(self, metadata: ArticleMetadata, content_flags: Dict[str, bool]):
        """Обновление флагов содержания в метаданных"""
        metadata.technical_metadata.content_flags = ContentFlags(**content_flags)
    
    def update_section_structure(self, metadata: ArticleMetadata, section_structure: List[Dict]):
        """Обновление структуры секций в метаданных"""
        metadata.article["section_structure"] = section_structure