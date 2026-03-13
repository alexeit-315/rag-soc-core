from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import re  # добавил эту строку, так как re используется в методе _analyze_content_flags
import logging

from bs4 import BeautifulSoup

from ..models.config import ConverterConfig
from ..models.schemas import ArticleMetadata, RelatedArticle, InternalLink
from ..models.statistics import ConversionStats, ValidationStats
from ..models.schemas import FirmwareVersions, Platforms
from ..models.schemas import ExternalLink
from ..models.schemas import InternalLink

from ..utils.logger import HDXLogger
from ..utils.file_utils import FileUtils
from ..utils.naming_utils import NamingUtils
from ..utils.image_processor import ImageProcessor
from ..utils.path_resolver import PathResolver
from ..utils.platform_patterns import PlatformPatterns

from ..parsers.html_parser import HTMLParser
from ..parsers.metadata_parser import MetadataParser
from ..parsers.navigation_parser import NavigationParser
from ..parsers.link_processor import LinkProcessor

from ..core.metadata_manager import MetadataManager
from ..core.content_processor import ContentProcessor
from ..core.validator import MetadataValidator
from ..core.stats_collector import StatisticsCollector

from ..writers.file_writer import FileWriter
from ..writers.json_writer import JSONWriter
from ..writers.markdown_writer import MarkdownWriter
from ..writers.text_writer import TextWriter
from ..writers.html_backup_writer import HTMLBackupWriter

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    tqdm = lambda x, **kwargs: x

class HDXConverter:
    def __init__(self, config: ConverterConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Создание директорий
        self._create_directories()
        
        # Инициализация утилит
        self.file_utils = FileUtils()
        self.naming_utils = NamingUtils(config)
        self.path_resolver = PathResolver(
            self.temp_extract_dir, self.html_backup_dir, config.skip_extract
        )
        self.image_processor = ImageProcessor(self.images_dir, self.temp_extract_dir)

        # Инициализация парсеров
        self.html_parser = HTMLParser()
        self.metadata_parser = MetadataParser()
        self.navigation_parser = NavigationParser(self.path_resolver)
        self.link_processor = LinkProcessor(self.path_resolver)

        # Инициализация менеджеров
        self.metadata_manager = MetadataManager(config, self.path_resolver)

        # === ИСПРАВЛЕНИЕ: Сначала создаем stats_collector ===
        self.stats_collector = StatisticsCollector()
        # === КОНЕЦ ИСПРАВЛЕНИЯ ===

        self.content_processor = ContentProcessor(
            config,
            self.path_resolver,
            self.image_processor,
            resolve_link_callback=self._resolve_link_target,
            logger=self.logger
        )
        self.validator = MetadataValidator(config, logger=self.logger)

        # === ИСПРАВЛЕНИЕ: Передаем stats_collector в ImageProcessor после его создания ===
        self.image_processor.stats_collector = self.stats_collector
        # === КОНЕЦ ИСПРАВЛЕНИЯ ===
        
        # Инициализация писателей
        self.file_writer = FileWriter(config, logger=self.logger)
        self.json_writer = JSONWriter(config, logger=self.logger)
        self.markdown_writer = MarkdownWriter(config, logger=self.logger)
        self.text_writer = TextWriter(config, logger=self.logger)
        self.html_backup_writer = HTMLBackupWriter(config, logger=self.logger)
        
        # Хранилища данных
        self.filename_mapping: Dict[str, Dict] = {}
        self.title_mapping: Dict[str, List] = {}
        self.topic_links: Dict[str, List] = {}
        
        # Глобальные метаданные
        self.global_firmware_versions = config.global_firmware_versions.copy()
        self.global_platforms = config.global_platforms.copy()

        # Статьи с метаданными для интерактивного подтверждения
        self.firmware_articles = []
        self.platform_articles = []
        
        self.stats_collector.start_conversion()

        # Атрибут для хранения пути к HDX файлу
        self.hdx_file_path = None
    
    def _create_directories(self):
        """Создание структуры директорий"""
        # Основные директории
        self.images_dir = self.config.output_dir / self.config.images_dir_name
        self.metadata_dir = self.config.output_dir / self.config.metadata_dir_name
        self.html_backup_dir = self.config.output_dir / self.config.html_backup_dir_name
        self.txt_output_dir = self.config.output_dir / self.config.txt_dir_name
        self.md_output_dir = self.config.output_dir / self.config.md_dir_name
        self.json_data_dir = self.config.output_dir / self.config.json_data_dir_name  # ДОБАВЛЕНО
        self.temp_extract_dir = self.config.output_dir / self.config.temp_extract_dir_name

        # Создание директорий
        directories = [
            self.config.output_dir,
            self.images_dir,
            self.metadata_dir,
            self.html_backup_dir,
            self.txt_output_dir,
            self.md_output_dir,
            self.json_data_dir  # ДОБАВЛЕНО
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def convert(self, hdx_file_path: Path):
        """Основной метод конвертации"""
        try:
            self.logger.debug(f"Starting conversion of {hdx_file_path}")

            # СОХРАНЯЕМ путь к HDX файлу для вычисления hdx_hash и имени файла
            self.hdx_file_path = hdx_file_path

            # Передаем имя HDX файла в конфигурацию для использования в metadata_manager
            self.hdx_file_path = hdx_file_path

            # Шаг 1: Извлечение HDX
            if not self.config.skip_extract:
                self._extract_hdx(hdx_file_path)

            # Шаг 2: Сбор информации о статьях
            self._collect_topic_info()

            # Шаг 3: Поиск статей с метаданными
            self._find_metadata_articles()

            # Шаг 4: Подтверждение глобальных метаданных
            if not self.config.skip_extract:
                self._confirm_global_metadata()

            # Шаг 5: Обработка контента
            self._process_html_content()

            # Шаг 6: Создание файлов навигации
            self._create_navigation_files()

            # Шаг 7: Сохранение всех метаданных
            self._save_all_metadata()

            # Шаг 8: Вывод статистики
            self.stats_collector.end_conversion()
            self._print_statistics()

            # Шаг 9: Вывод предупреждений о пропущенных файлах
            if self.config.save_skipped_files:
                self._print_skipped_files_warnings()

            self.logger.debug("Conversion completed successfully")

        except Exception as e:
            # ERROR оставляем - они должны выводиться
            self.logger.error(f"Conversion failed: {e}")
            self.stats_collector.increment_stat("errors_encountered")
            raise
        finally:
            if not self.config.skip_extract:
                self._cleanup()

    def _extract_hdx(self, hdx_file_path: Path):
        """Извлечение HDX файла"""
        self.logger.debug(f"Extracting HDX file: {hdx_file_path}")
        self.file_utils.extract_zip(hdx_file_path, self.temp_extract_dir)
        self.logger.debug(f"Successfully extracted to: {self.temp_extract_dir}")

    # core/converter.py - добавляем отладку
    def _collect_topic_info(self):
        """Сбор информации о статьях"""
        self.logger.debug("Collecting topic information...")

        # Определение источника файлов
        source_dir = self.html_backup_dir if self.config.skip_extract else self.temp_extract_dir

        # Поиск HTML файлов С УЧЕТОМ max_articles
        html_files = self.file_utils.find_all_html_files(source_dir, self.config.max_articles)

        self.logger.debug(f"Found {len(html_files)} HTML files for info collection")
        if self.config.max_articles:
            self.logger.debug(f"Limited to first {self.config.max_articles} files")

        # Используем прогресс-бар
        pbar_desc = "Collecting topic info"
        successful_count = 0
        failed_count = 0

        for html_file in tqdm(html_files, desc=pbar_desc, disable=not HAS_TQDM):
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                soup = BeautifulSoup(html_content, 'html.parser')

                # Извлечение заголовка и DC.Identifier
                title = self.html_parser.extract_title(soup, html_file)
                dc_identifier = self.metadata_parser.extract_dc_identifier(soup)

                if not dc_identifier:
                    self.metadata_manager.add_file_without_dc_identifier(html_file)
                    self.stats_collector.add_skipped_file(
                        str(html_file), "Missing DC.Identifier"
                    )
                    failed_count += 1
                    continue

                # Проверка уникальности DC.Identifier
                if not self.metadata_manager.register_dc_identifier(dc_identifier, html_file):
                    self.stats_collector.add_skipped_file(
                        str(html_file), "Duplicate DC.Identifier",
                        {"dc_identifier": dc_identifier}
                    )
                    failed_count += 1
                    continue

                # Генерация имен файлов
                filenames = self.naming_utils.generate_filenames(title, dc_identifier, html_file.stem)

                # Проверка длины имен файлов
                html_ok, html_len = self.naming_utils.check_filename_length(filenames['html'])
                md_ok, md_len = self.naming_utils.check_filename_length(filenames['md'])

                if not html_ok or not md_ok:
                    self.stats_collector.add_skipped_file(
                        str(html_file), "Filename too long",
                        {"html_length": html_len, "md_length": md_len}
                    )
                    failed_count += 1
                    continue

                # Сохранение маппинга
                self.filename_mapping[html_file.name] = filenames
                rel_path = html_file.relative_to(source_dir)
                self.filename_mapping[str(rel_path)] = filenames

                # Сохранение маппинга заголовков
                if title not in self.title_mapping:
                    self.title_mapping[title] = []
                self.title_mapping[title].append({
                    'html_file': html_file.name,
                    'dc_identifier': dc_identifier,
                    'md_filename': filenames['md'],
                    'html_filename': filenames['html']
                })

                # Создание метаданных
                hdx_hash = self.file_utils.calculate_file_hash(self.config.output_dir / ".." / "source.hdx")
                metadata = self.metadata_manager.create_article_metadata(
                    soup, html_file, title, dc_identifier,
                    filenames['html'], filenames['md'], hdx_hash
                )

                # Сохранение метаданных
                self.metadata_manager.add_metadata(html_file.name, metadata)

                successful_count += 1
                self.logger.debug(f"Collected info: {html_file.name} -> MD: {filenames['md']}")

            except Exception as e:
                failed_count += 1
                self.logger.debug(f"Could not collect info for {html_file}: {e}")

        self.logger.debug(f"Successfully collected info for {successful_count} files, failed for {failed_count} files")

    def _find_metadata_articles(self):
        """Поиск статей с метаданными о прошивке и платформах"""
        self.logger.debug("Searching for articles with firmware and platform metadata...")

        self.firmware_articles = []
        self.platform_articles = []

        for html_filename, metadata in self.metadata_manager.metadata_store.items():
            try:
                # Определяем путь к файлу
                if self.config.skip_extract:
                    html_file = self.html_backup_dir / metadata.source.html_path
                else:
                    html_file = self.temp_extract_dir / metadata.source.html_path

                if not html_file.exists():
                    continue

                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                content_lower = content.lower()
                title_lower = metadata.article.get("title", "").lower()

                # Поиск версий прошивки
                firmware_keywords = ['software version', 'firmware', 'v600r', 'v500r', 'release']
                for keyword in firmware_keywords:
                    if keyword in title_lower or keyword in content_lower:
                        versions = self.metadata_parser.extract_firmware_versions(content)
                        if versions:
                            self.firmware_articles.append({
                                'filename': html_filename,
                                'title': metadata.article.get("title", ""),
                                'versions': versions,
                                'content_preview': content[:500] + "..."
                            })
                        break

                # Поиск платформ
                platform_keywords = ['product model', 'compatible', 'supported device', 'platform', 'usg']
                for keyword in platform_keywords:
                    if keyword in title_lower or keyword in content_lower:
                        platforms = self.metadata_parser.extract_platforms(content)
                        if platforms:
                            self.platform_articles.append({
                                'filename': html_filename,
                                'title': metadata.article.get("title", ""),
                                'platforms': platforms,
                                'content_preview': content[:500] + "..."
                            })
                        break

            except Exception as e:
                self.logger.debug(f"Could not analyze {html_filename}: {e}")

        self.logger.debug(f"Found {len(self.firmware_articles)} firmware articles, {len(self.platform_articles)} platform articles")
    
    def _confirm_global_metadata(self):
        """Подтверждение глобальных метаданных с заполнением compatible_models - ИСПРАВЛЕННАЯ ВЕРСИЯ (пункт 5)"""
        if not hasattr(self, 'firmware_articles') or not hasattr(self, 'platform_articles'):
            self.logger.debug("Metadata articles not found, skipping confirmation")
            return

        print("\n" + "="*60)
        print("ГЛОБАЛЬНЫЕ МЕТАДАННЫЕ HDX ДОКУМЕНТАЦИИ")
        print("="*60)

        # ИСПРАВЛЕНИЕ: Всегда показываем секцию прошивки, даже если статей не найдено
        print("\n=== ВЕРСИИ ПРОШИВКИ ===")

        if self.firmware_articles:
            for i, article in enumerate(self.firmware_articles[:3]):
                print(f"\n{i+1}. Статья: {article['title']}")
                print(f"   Файл: {article['filename']}")
                print(f"   Найденные версии: {', '.join(article['versions'])}")
                print(f"   Контекст: {article['content_preview'][:200]}...")

            if len(self.firmware_articles) > 3:
                print(f"\n... и еще {len(self.firmware_articles) - 3} статей")
        else:
            print("\nСтатьи с информацией о версиях прошивки не найдены.")
            print("Можно ввести версию вручную или пропустить.")

        print("\nВыберите версию прошивки для всего документа:")
        print("1. Использовать версию из первой статьи (если доступно)")
        print("2. Ввести версию вручную")
        print("3. Пропустить (оставить пустым)")

        try:
            choice = input("Ваш выбор (1-3): ").strip()

            if choice == '1' and self.firmware_articles:
                # Фильтруем IP-адреса из версий
                filtered_versions = []
                for version in self.firmware_articles[0]["versions"]:
                    # Проверяем, что это не IP-адрес (формат x.x.x.x)
                    if not re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', version):
                        filtered_versions.append(version)

                if filtered_versions:
                    self.global_firmware_versions["primary"] = filtered_versions[0]
                    self.global_firmware_versions["all_versions"] = filtered_versions
                    print(f"Установлена версия: {self.global_firmware_versions['primary']}")
                else:
                    print("Не найдено корректных версий прошивки")
            elif choice == '2':
                version = input("Введите версию прошивки (например, V600R024C10): ").strip()
                if version:
                    self.global_firmware_versions["primary"] = version
                    self.global_firmware_versions["all_versions"] = [version]
                    print(f"Установлена версия: {version}")

            self.global_firmware_versions["confirmed_by_user"] = True
            self.global_firmware_versions["applicability_scope"] = "entire_hdx"

        except Exception as e:
            self.logger.error(f"Error in firmware confirmation: {e}")
            self.global_firmware_versions["confirmed_by_user"] = True
            self.global_firmware_versions["applicability_scope"] = "entire_hdx"

        if self.platform_articles:
            print("\n=== ПЛАТФОРМЫ И МОДЕЛИ ===")
            for i, article in enumerate(self.platform_articles[:3]):
                print(f"\n{i+1}. Статья: {article['title']}")
                print(f"   Файл: {article['filename']}")
                print(f"   Найденные платформы: {', '.join(article['platforms'][:10])}")
                if len(article['platforms']) > 10:
                    print(f"   ... и еще {len(article['platforms']) - 10}")
                print(f"   Контекст: {article['content_preview'][:200]}...")

            if len(self.platform_articles) > 3:
                print(f"\n... и еще {len(self.platform_articles) - 3} статей")

            print("\nВыберите платформы для всего документа:")
            print("1. Использовать платформы из первой статьи")
            print("2. Ввести основную серию вручную")
            print("3. Пропустить (оставить пустым)")

            try:
                choice = input("Ваш выбор (1-3): ").strip()

                if choice == '1' and self.platform_articles:
                    platforms = self.platform_articles[0]["platforms"]

                    # ИСПРАВЛЕНИЕ: Заполняем compatible_models из найденных платформ
                    compatible_models = []
                    for platform in platforms:
                        # Ищем серию продуктов
                        is_series = False
                        for pattern in PlatformPatterns.PRODUCT_SERIES_PATTERNS:
                            if re.match(pattern, platform, re.IGNORECASE):
                                is_series = True
                                if not self.global_platforms["product_series"]:
                                    self.global_platforms["product_series"] = platform
                                break
                        # Все платформы добавляем в compatible_models
                        if platform not in compatible_models:
                            compatible_models.append(platform)

                    self.global_platforms["compatible_models"] = compatible_models
                    print(f"Установлена серия: {self.global_platforms['product_series']}")
                    print(f"Найдено моделей: {len(compatible_models)}")
                elif choice == '2':
                    series = input("Введите основную серию продуктов (например, USG6000F): ").strip()
                    if series:
                        self.global_platforms["product_series"] = series
                        # Ищем совместимые модели в статьях
                        all_models = []
                        for article in self.platform_articles:
                            for platform in article["platforms"]:
                                if platform not in all_models:
                                    all_models.append(platform)
                        self.global_platforms["compatible_models"] = all_models

                self.global_platforms["confirmed_by_user"] = True
                self.global_platforms["applicability_scope"] = "entire_hdx"

            except Exception as e:
                self.logger.error(f"Error in platform confirmation: {e}")

        print("\n" + "="*60)
        print("Подтверждение завершено")
        print("="*60)
    
    def _process_html_content(self):
        """Обработка HTML контента"""
        self.logger.debug("Processing HTML content...")

        source_dir = self.html_backup_dir if self.config.skip_extract else self.temp_extract_dir

        # Находим HTML файлы для резервного копирования С УЧЕТОМ max_articles
        html_files_for_backup = self.file_utils.find_all_html_files(source_dir, self.config.max_articles)

        self.logger.debug(f"Processing {len(html_files_for_backup)} HTML files")

        # Резервное копирование
        if not self.config.skip_extract and self.config.backup_html:
            self.logger.debug(f"Backing up {len(html_files_for_backup)} HTML files...")
            backup_pbar = tqdm(html_files_for_backup, desc="Backing up HTML", disable=not HAS_TQDM)
            for html_file in backup_pbar:
                try:
                    filenames = self.filename_mapping.get(html_file.name)
                    if filenames:
                        self.html_backup_writer.backup_html(
                            html_file, filenames['html'], self.html_backup_dir
                        )
                        self.stats_collector.increment_stat("html_backups_created")
                        self.stats_collector.increment_stat("total_files_created")
                except Exception as e:
                    self.logger.error(f"Failed to backup {html_file}: {e}")

        # Фильтрация файлов с метаданными для обработки
        html_files_to_process = [f for f in html_files_for_backup if f.name in self.metadata_manager.metadata_store]

        # Дополнительное ограничение (на всякий случай)
        if self.config.max_articles:
            html_files_to_process = html_files_to_process[:self.config.max_articles]

        self.logger.debug(f"Files to process after filtering: {len(html_files_to_process)}")

        if not html_files_to_process:
            self.logger.error("No files to process! Check metadata collection.")
            return

        # Используем прогресс-бар для обработки
        process_pbar = tqdm(html_files_to_process, desc="Processing articles", disable=not HAS_TQDM)
        for i, html_file in enumerate(process_pbar):
            try:
                # Обработка файла
                self._process_single_html_file(html_file)

                if HAS_TQDM:
                    process_pbar.set_postfix({"file": html_file.name[:30] + "..."})

            except Exception as e:
                self.logger.error(f"Error processing HTML file {html_file}: {e}")
                self.stats_collector.increment_stat("errors_encountered")

    def _process_single_html_file(self, html_file: Path):
        """Обработка одного HTML файла - НОВАЯ ВЕРСИЯ СО STRUCTURED_DATA"""
        # === ИСПРАВЛЕНИЕ: Добавлено INFO логирование ===
        self.logger.info(f"Начало обработки файла {html_file.name}")
        # === КОНЕЦ ИСПРАВЛЕНИЯ ===
        self.logger.debug(f"=== НАЧАЛО ОБРАБОТКИ ФАЙЛА {html_file.name} ===")

        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # Извлечение контента В НОВОМ ФОРМАТЕ
        title = self.html_parser.extract_title(soup, html_file)
        self.logger.debug(f"Извлечен заголовок: '{title}'")

        structured_data, internal_links, external_links = self.content_processor.extract_content_with_links(
            soup, html_file
        )

        self.logger.debug(f"Получены structured_data: секций={len(structured_data.get('content', []))}, "
                         f"ссылок={len(structured_data.get('links', {}).get('internal', []))}")

        # Получение метаданных
        metadata = self.metadata_manager.get_metadata_by_filename(html_file.name)
        if metadata:
            self.logger.debug(f"Найдены метаданные для {html_file.name}")

            # Вычисляем hdx_hash и заполняем hdx_filename
            if self.hdx_file_path and self.hdx_file_path.exists():
                hdx_hash = self.file_utils.calculate_file_hash(self.hdx_file_path)
                metadata.source.hdx_hash = hdx_hash
                metadata.source.hdx_filename = self.hdx_file_path.name

            # Обновление информации о ссылках ИЗ STRUCTURED_DATA
            self._update_links_in_metadata_from_structured(metadata, structured_data)

            # Обновление флагов содержания
            content_flags = self._analyze_content_flags_from_structured(structured_data)
            self.metadata_manager.update_content_flags(metadata, content_flags)

            # Обновление структуры секций ИЗ STRUCTURED_DATA
            section_structure = self._extract_section_structure_from_structured(structured_data)
            self.metadata_manager.update_section_structure(metadata, section_structure)

            # === ИСПРАВЛЕНИЕ: УБРАНА ВАЛИДАЦИЯ ЗДЕСЬ ===
            # Валидация будет выполнена в _save_all_metadata() после полного заполнения
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===
        else:
            self.logger.error(f"Метаданные не найдены для {html_file.name}")
            return

        # Получение имен файлов
        filenames = self.filename_mapping.get(html_file.name)
        if not filenames:
            self.logger.error(f"Нет маппинга имен файлов для {html_file.name}")
            return

        self.logger.debug(f"Имена файлов для {html_file.name}: {filenames}")

        # Создание навигации
        navigation = self._create_navigation_section(soup, html_file)

        # ДОБАВЛЕНО: Сохранение structured_data в JSON
        self._save_structured_data(structured_data, filenames['md'])

        # Генерация TXT (используем structured_data)
        if self.config.generate_text:
            txt_content = self.text_writer.format_structured_content(structured_data, navigation)
            result = self.text_writer.save_text_file(
                txt_content, filenames['md'], self.txt_output_dir, title
            )
            if result:
                self.stats_collector.increment_stat("txt_files_created")
                self.stats_collector.increment_stat("total_files_created")
                # === ИСПРАВЛЕНИЕ: Добавлено INFO логирование ===
                self.logger.info(f"Создан TXT файл: {result.name}")
                # === КОНЕЦ ИСПРАВЛЕНИЯ ===
                self.logger.debug(f"Создан TXT файл: {result}")
            else:
                self.logger.error(f"Ошибка создания TXT файла для {html_file.name}")

        # Генерация Markdown (используем structured_data)
        if self.config.generate_markdown:
            md_content = self.markdown_writer.convert_structured_to_markdown(
                structured_data, navigation, html_file, metadata.model_dump(mode='json') if metadata else {}
            )
            result = self.markdown_writer.save_markdown_file(
                md_content, filenames['md'], self.md_output_dir, title
            )
            if result:
                self.stats_collector.increment_stat("md_files_created")
                self.stats_collector.increment_stat("total_files_created")
                # === ИСПРАВЛЕНИЕ: Добавлено INFO логирование ===
                self.logger.info(f"Создан MD файл: {result.name}")
                # === КОНЕЦ ИСПРАВЛЕНИЯ ===
                self.logger.debug(f"Создан MD файл: {result}")
            else:
                self.logger.error(f"Ошибка создания MD файла для {html_file.name}")

        # Сохранение статистики
        self.stats_collector.increment_stat("html_files_processed")
        self.stats_collector.increment_stat("topics_processed")
        self.stats_collector.increment_stat("internal_links_preserved", len(structured_data.get("links", {}).get("internal", [])))

        # Подсчет таблиц из structured_data
        table_count = self._count_tables_in_structured(structured_data)
        self.stats_collector.increment_stat("tables_processed", table_count)

        self.logger.debug(f"=== УСПЕШНО ОБРАБОТАН {html_file.name} ===")
        # === ИСПРАВЛЕНИЕ: Добавлено INFO логирование ===
        self.logger.info(f"Завершена обработка файла {html_file.name}")
        # === КОНЕЦ ИСПРАВЛЕНИЯ ===

    def _analyze_content_flags(self, content: str) -> Dict[str, bool]:
        """Анализ флагов содержания"""
        flags = {
            "contains_cli_commands": bool(re.search(r'^\s*[\w\-]+\s+[\w\-]+', content, re.MULTILINE)),
            "contains_configuration_steps": bool(re.search(r'step\s+\d+|procedure|configuration', content, re.IGNORECASE)),
            "contains_tables": ' | ' in content,
            "contains_code_examples": '```' in content,
            "contains_warnings": bool(re.search(r'\*\*Note:\*\*|\*\*Warning:\*\*', content))
        }
        return flags

    def _create_navigation_section(self, soup: BeautifulSoup, html_file: Path) -> str:
        """Создание раздела навигации - ИСПРАВЛЕННАЯ ВЕРСИЯ

        ИСПРАВЛЕНИЕ: Не используется, так как навигация теперь в structured_data
        """
        return ""  # Возвращаем пустую строку, так как навигация теперь в structured_data
    
    def _resolve_link_target(self, href: str, source_file: Path) -> Optional[Dict]:
        """Разрешение целевой ссылки - УЛУЧШЕННАЯ ВЕРСИЯ"""
        try:
            if not href or not href.lower().endswith('.html'):
                return None

            # Извлекаем оригинальное имя файла
            original_filename = Path(href).name

            # 1. Сначала ищем в filename_mapping по оригинальному имени
            target_info = None
            for orig_name, filenames in self.filename_mapping.items():
                if orig_name == original_filename:
                    target_info = {
                        'target': filenames['html'],
                        'title': '',  # Будет заполнено
                        'dc_identifier': '',  # Будет заполнено
                        'md_filename': filenames['md'],
                        'html_path': href
                    }
                    break

            if not target_info:
                # Если не нашли в маппинге, используем оригинальное имя
                target_info = {
                    'target': original_filename,
                    'title': '',
                    'dc_identifier': '',
                    'md_filename': original_filename.replace('.html', '.md'),
                    'html_path': href
                }

            # 2. Ищем метаданные целевой статьи
            # Сначала ищем по новому имени (target)
            if target_info['target'] in self.metadata_manager.metadata_store:
                metadata = self.metadata_manager.get_metadata_by_filename(target_info['target'])
                if metadata:
                    target_info['title'] = metadata.article.get("title", "")
                    target_info['dc_identifier'] = metadata.article.get("dc_identifier", "")
                    return target_info

            # 3. Ищем по оригинальному имени в хранилище метаданных
            for filename, metadata in self.metadata_manager.metadata_store.items():
                # Проверяем несколько вариантов
                if (metadata.source.html_filename == original_filename or
                    metadata.source.html_path.endswith(original_filename)):
                    target_info['title'] = metadata.article.get("title", "")
                    target_info['dc_identifier'] = metadata.article.get("dc_identifier", "")
                    return target_info

            # 4. Пытаемся прочитать HTML файл напрямую
            source_dir = self.html_backup_dir if self.config.skip_extract else self.temp_extract_dir
            possible_locations = [
                source_file.parent / href,
                source_dir / href,
                source_dir / original_filename
            ]

            for location in possible_locations:
                if location.exists():
                    try:
                        with open(location, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        soup = BeautifulSoup(html_content, 'html.parser')

                        # Извлекаем заголовок и идентификатор
                        html_parser = HTMLParser()
                        title = html_parser.extract_title(soup, location)

                        metadata_parser = MetadataParser()
                        dc_identifier = metadata_parser.extract_dc_identifier(soup)

                        if title or dc_identifier:
                            target_info['title'] = title
                            target_info['dc_identifier'] = dc_identifier
                            return target_info
                    except Exception as e:
                        continue

            # 5. Если ничего не нашли, возвращаем хотя бы то, что есть
            return target_info

        except Exception as e:
            self.logger.debug(f"Could not resolve link target {href}: {e}")
            return None

    def _create_navigation_files(self):
        """Создание файлов навигации"""
        if not self.topic_links:
            return
        
        link_map_content = ["=== TOPIC LINK MAP ===", ""]
        for source, links in self.topic_links.items():
            link_map_content.append(f"FROM: {source}")
            for link_text, href, target in links:
                link_map_content.append(f"  - {link_text} -> {target}")
            link_map_content.append("")
        
        map_file = self.config.output_dir / "topic_links_map.txt"
        with open(map_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(link_map_content))
    
    def _save_all_metadata(self):
        """Сохранение всех метаданных"""
        if not self.config.generate_json_metadata:
            return

        self.logger.debug("Saving metadata files...")
        all_metadata = self.metadata_manager.get_all_metadata()

        for metadata in all_metadata.values():
            # Применение глобальных метаданных
            if self.global_firmware_versions["confirmed_by_user"]:
                metadata.technical_metadata.firmware_versions = FirmwareVersions(
                    primary=self.global_firmware_versions.get("primary", ""),
                    all_versions=self.global_firmware_versions.get("all_versions", []),
                    applicability_scope=self.global_firmware_versions.get("applicability_scope", "entire_hdx"),
                    confirmed_by_user=self.global_firmware_versions.get("confirmed_by_user", True)
                )

            if self.global_platforms["confirmed_by_user"]:
                metadata.technical_metadata.platforms = Platforms(
                    product_series=self.global_platforms.get("product_series", ""),
                    compatible_models=self.global_platforms.get("compatible_models", []),
                    model_limitations=self.global_platforms.get("model_limitations", {}),
                    applicability_scope=self.global_platforms.get("applicability_scope", "entire_hdx"),
                    confirmed_by_user=self.global_platforms.get("confirmed_by_user", True)
                )

            # === ИСПРАВЛЕНИЕ: ВАЛИДАЦИЯ ПОСЛЕ ПОЛНОГО ЗАПОЛНЕНИЯ МЕТАДАННЫХ ===
            if self.config.validate_metadata:
                validation = self.validator.validate_metadata(metadata)
                metadata.validation = validation
                self.stats_collector.add_validation_result(
                    validation.is_valid,
                    validation.missing_fields.mandatory,
                    validation.missing_fields.recommended,
                    validation.missing_fields.optional
                )
                self.logger.debug(f"Результат валидации для {metadata.source.html_filename}: valid={validation.is_valid}")
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===

            # Сохранение в JSON
            result = self.json_writer.save_metadata(metadata, self.metadata_dir)
            if result:
                self.stats_collector.increment_stat("metadata_files_created")
                self.stats_collector.increment_stat("total_files_created")
    
    def _print_statistics(self):
        """Вывод статистики"""
        if not self.config.print_statistics:
            return

        stats = self.stats_collector.get_statistics_summary()
        conv_stats = stats["conversion"]
        val_stats = stats["validation"]

        stats_message = f"""
    === CONVERSION STATISTICS ===
    Total HTML files processed: {conv_stats['html_files_processed']}
    Total topics created: {conv_stats['topics_processed']}
    Total files created: {conv_stats['total_files_created']}
      - TXT files: {conv_stats['txt_files_created']}
      - MD files: {conv_stats['md_files_created']}
      - Metadata files: {conv_stats['metadata_files_created']}
      - HTML backups: {conv_stats['html_backups_created']}
    Total images copied: {conv_stats['total_images_copied']}
    Total tables processed: {conv_stats['tables_processed']}
    Internal links preserved: {conv_stats['internal_links_preserved']}
    Name conflicts resolved: {conv_stats['name_conflicts_resolved']}
    Errors encountered: {conv_stats['errors_encountered']}

    Conversion duration: {stats['duration']:.2f} seconds

    === VALIDATION STATISTICS ===
    Total articles: {val_stats['total_articles']}
    Valid articles: {val_stats['valid_articles']}
    Articles with errors: {val_stats['articles_with_errors']}
    Articles with warnings: {val_stats['articles_with_warnings']}
    ============================
    """
        # === ИСПРАВЛЕНИЕ: Статистика всегда выводится в консоль print'ом ===
        # Выводим статистику только print'ом, не через логгер (чтобы видеть во всех режимах)
        print(stats_message)
        # Логируем статистику в файл с debug уровнем
        self.logger.info(stats_message.strip())
        # === КОНЕЦ ИСПРАВЛЕНИЯ ===
    
    def _print_skipped_files_warnings(self):
        """Вывод предупреждений о пропущенных файлах"""
        skipped_files = self.stats_collector.skipped_files
        if not skipped_files:
            return

        # Группировка по причине
        by_reason = {}
        for file_info in skipped_files:
            reason = file_info.reason
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(file_info)

        warning_message = "\n=== SKIPPED FILES WARNINGS ===\n"
        for reason, files in by_reason.items():
            warning_message += f"\n{reason} ({len(files)} files):\n"
            for file_info in files[:5]:  # Показываем только первые 5
                warning_message += f"  - {file_info.file_path}\n"
            if len(files) > 5:
                warning_message += f"  ... and {len(files) - 5} more files\n"

        # Выводим warning в файл, но не в консоль
        self.logger.debug(warning_message)

        # Сохранение в файл
        skipped_file = self.config.output_dir / "skipped_files.txt"
        with open(skipped_file, 'w', encoding='utf-8') as f:
            f.write("=== SKIPPED FILES LIST ===\n\n")
            for reason, files in by_reason.items():
                f.write(f"{reason.upper()}:\n")
                f.write("="*40 + "\n")
                for file_info in files:
                    f.write(f"{file_info.file_path}\n")
                    if file_info.details:
                        for key, value in file_info.details.items():
                            f.write(f"  {key}: {value}\n")
                f.write(f"\nTotal: {len(files)} files\n\n")

    # В функции _cleanup()
    def _cleanup(self):
        """Очистка временных файлов"""
        if self.temp_extract_dir.exists():
            self.file_utils.clean_temp_directory(self.temp_extract_dir)
            self.logger.debug("Cleaned up temporary files")

    def _update_links_in_metadata(self, metadata, internal_links, external_links):
        """Обновление информации о ссылках в метаданных - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        # 1. Обработка external_links (просто копируем)
        if external_links:
            metadata.relations.external_links = [
                ExternalLink(text=link["text"], url=link["url"])
                for link in external_links
            ]

        # 2. Обработка internal_links - создаем объекты InternalLink
        normalized_links = []

        for link_text, href, target in internal_links:
            # Получаем информацию о целевой статье
            target_info = self._resolve_link_target(href, metadata.source.html_path)

            # Создаем объект InternalLink
            normalized_links.append(InternalLink(
                text=link_text,
                dc_identifier=target_info.get('dc_identifier', '') if target_info else '',
                html_filename=target_info.get('target', '') if target_info else '',
                html_path=href if href else '',
                md_filename=target_info.get('md_filename', '') if target_info else ''
            ))

        if normalized_links:
            metadata.relations.internal_links = normalized_links

        self.logger.debug(f"Updated {len(normalized_links)} internal links in metadata")

    def _update_links_in_metadata_from_structured(self, metadata, structured_data: Dict[str, Any]):
        """Обновление информации о ссылках в метаданных ИЗ STRUCTURED_DATA"""
        logger = self.logger

        # 1. Обработка external_links
        external_links = []
        for link_info in structured_data.get("links", {}).get("external", []):
            external_links.append(
                ExternalLink(
                    text=link_info.get("text", ""),
                    url=link_info.get("href", "")
                )
            )

        if external_links:
            metadata.relations.external_links = external_links
            logger.debug(f"Добавлено external links: {len(external_links)}")

        # 2. Обработка internal_links - создаем объекты InternalLink
        normalized_links = []

        for link_info in structured_data.get("links", {}).get("internal", []):
            href = link_info.get("href", "")
            if not href:
                continue

            # Получаем информацию о целевой статье
            target_info = self._resolve_link_target(href, metadata.source.html_path)

            # Создаем объект InternalLink
            normalized_links.append(InternalLink(
                text=link_info.get("text", ""),
                dc_identifier=target_info.get('dc_identifier', '') if target_info else '',
                html_filename=target_info.get('target', '') if target_info else '',
                html_path=href,
                md_filename=target_info.get('md_filename', '') if target_info else ''
            ))

        if normalized_links:
            metadata.relations.internal_links = normalized_links
            logger.debug(f"Добавлено internal links: {len(normalized_links)}")

    def _analyze_content_flags_from_structured(self, structured_data: Dict[str, Any]) -> Dict[str, bool]:
        """Анализ флагов содержания ИЗ STRUCTURED_DATA"""

        flags = {
            "contains_cli_commands": False,
            "contains_configuration_steps": False,
            "contains_tables": False,
            "contains_code_examples": False,
            "contains_warnings": False
        }

        # Рекурсивный поиск
        def search_in_element(element):
            if isinstance(element, dict):
                if element.get("type") == "code_block":
                    content = element.get("content", "")
                    if content and re.search(r'^\s*[\w\-]+\s+[\w\-]+', content, re.MULTILINE):
                        flags["contains_cli_commands"] = True
                        flags["contains_code_examples"] = True

                elif element.get("type") in ["section", "paragraph"]:
                    content = element.get("content", "")
                    if isinstance(content, str):
                        if 'step' in content.lower() or 'procedure' in content.lower() or 'configuration' in content.lower():
                            flags["contains_configuration_steps"] = True
                        if '**Note:**' in content or '**Warning:**' in content:
                            flags["contains_warnings"] = True

                # Рекурсивный обход
                for key, value in element.items():
                    if key != "type":
                        search_in_element(value)

            elif isinstance(element, list):
                for item in element:
                    search_in_element(item)

        # Поиск во всем контенте
        for content_item in structured_data.get("content", []):
            search_in_element(content_item)

        return flags

    def _extract_section_structure_from_structured(self, structured_data: Dict[str, Any]) -> List[Dict]:
        """Извлечение структуры разделов ИЗ STRUCTURED_DATA"""
        sections = []

        for i, content_item in enumerate(structured_data.get("content", [])):
            if content_item.get("type") == "section":
                section_id = f"section_{i+1}"
                title = content_item.get("title", "")

                if title and title != "Навигация":  # Пропускаем навигационную секцию
                    sections.append({
                        "section_id": section_id,
                        "title": title,
                        "type": "content"  # Можно уточнить логику определения типа
                    })

        self.logger.debug(f"Извлечено секций из structured_data: {len(sections)}")
        return sections

    def _count_tables_in_structured(self, structured_data: Dict[str, Any]) -> int:
        """Подсчет таблиц в structured_data"""
        table_count = 0

        # Рекурсивный поиск таблиц
        def search_tables(element):
            nonlocal table_count
            if isinstance(element, dict):
                if element.get("type") == "table":
                    table_count += 1
                # Рекурсивный обход
                for value in element.values():
                    if isinstance(value, (dict, list)):
                        search_tables(value)
            elif isinstance(element, list):
                for item in element:
                    search_tables(item)

        search_tables(structured_data)
        return table_count

    def _save_structured_data(self, structured_data: Dict[str, Any], base_filename: str):
        """Сохранение structured_data в JSON файл"""
        try:
            # Убираем расширение .md если оно уже есть
            if base_filename.lower().endswith('.md'):
                base_filename = base_filename[:-3]

            # Добавляем расширение .json
            filename = f"{base_filename}.json"

            # Сохраняем файл
            output_path = self.json_data_dir / filename

            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)

            self.stats_collector.increment_stat("json_data_files_created")
            self.stats_collector.increment_stat("total_files_created")

            # === ИСПРАВЛЕНИЕ: Добавлено INFO логирование ===
            self.logger.info(f"Создан JSON data файл: {output_path.name}")
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===
            self.logger.debug(f"Создан JSON data файл: {output_path}")

            return output_path

        except Exception as e:
            self.logger.error(f"Ошибка сохранения structured_data для {base_filename}: {e}")
            return None