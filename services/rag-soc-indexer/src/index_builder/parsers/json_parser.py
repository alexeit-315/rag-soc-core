#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parser for JSON files from HDX Converter
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
import logging


class JSONParser:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def is_data_json(self, filepath: Path) -> bool:
        """Проверяет, является ли JSON файлом данных (не метаданных)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Файлы данных имеют поле "content"
                if isinstance(data, dict) and "content" in data:
                    return True
                # Файлы метаданных имеют поле "metadata_version"
                if isinstance(data, dict) and "metadata_version" in data:
                    return False
        except Exception as e:
            self.logger.debug(f"Error checking {filepath}: {e}")

        # По умолчанию считаем по наличию поля "metadata" (данные)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return "metadata" in data and "content" in data
        except:
            return False

    def load_json_file(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Загружает JSON файл"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load {filepath}: {e}")
            return None

    def load_metadata(self, metadata_path: Path) -> Optional[Dict[str, Any]]:
        """Загружает метаданные"""
        data = self.load_json_file(metadata_path)
        if not data:
            return None

        # Проверяем, что это действительно метаданные
        if "metadata_version" not in data:
            self.logger.debug(f"File {metadata_path} does not look like metadata (no metadata_version)")

        return data

    def extract_text_from_content(self, content_item: Dict[str, Any]) -> str:
        """Рекурсивно извлекает текст из структуры content"""
        texts = []

        if isinstance(content_item, dict):
            item_type = content_item.get("type", "")

            if item_type == "paragraph":
                paragraph_content = content_item.get("content", "")
                if isinstance(paragraph_content, str):
                    texts.append(paragraph_content)
                elif isinstance(paragraph_content, list):
                    for sub_item in paragraph_content:
                        sub_text = self.extract_text_from_content(sub_item)
                        if sub_text:
                            texts.append(sub_text)

            elif item_type == "list":
                for item in content_item.get("items", []):
                    item_text = self.extract_text_from_content(item)
                    if item_text:
                        texts.append(item_text)

            elif item_type == "list_item":
                item_content = content_item.get("content", [])
                if not item_content and "text" in content_item:
                    texts.append(content_item.get("text", ""))
                else:
                    for sub_item in item_content:
                        sub_text = self.extract_text_from_content(sub_item)
                        if sub_text:
                            texts.append(sub_text)

            elif item_type == "code_block":
                code_text = content_item.get("content", "")
                if code_text:
                    texts.append(f"```\n{code_text}\n```")

            elif item_type == "link":
                link_text = content_item.get("text", "")
                if link_text:
                    texts.append(link_text)

            elif item_type == "text":
                text = content_item.get("content", "")
                if text:
                    texts.append(text)

            elif item_type == "image":
                alt = content_item.get("alt", "image")
                texts.append(f"[Image: {alt}]")

            elif item_type == "navigation":
                nav_text = content_item.get("content", "")
                if nav_text:
                    texts.append(nav_text)

            elif item_type == "section":
                section_title = content_item.get("title", "Section")
                section_texts = []
                for sub_item in content_item.get("content", []):
                    sub_text = self.extract_text_from_content(sub_item)
                    if sub_text:
                        section_texts.append(sub_text)
                if section_texts:
                    texts.append(f"\n## {section_title}\n" + "\n".join(section_texts))

            else:
                # Для неизвестных типов пробуем извлечь все строковые поля
                for key, value in content_item.items():
                    if key not in ["type", "list_type", "language"]:
                        if isinstance(value, str) and value:
                            texts.append(value)
                        elif isinstance(value, (dict, list)):
                            sub_text = self.extract_text_from_content(value)
                            if sub_text:
                                texts.append(sub_text)

        elif isinstance(content_item, list):
            for item in content_item:
                item_text = self.extract_text_from_content(item)
                if item_text:
                    texts.append(item_text)

        elif isinstance(content_item, str):
            if content_item.strip():
                texts.append(content_item.strip())

        # Фильтруем пустые строки и объединяем
        return "\n".join(filter(None, texts))

    def extract_sections(self, data_json: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Извлекает секции из структуры content"""
        sections = []
        content_list = data_json.get("content", [])

        for item in content_list:
            if item.get("type") == "section":
                title = item.get("title", "root")
                text = self.extract_text_from_content(item)
                if text.strip():
                    sections.append((title, text))
            else:
                # Если элемент не секция, но есть на верхнем уровне
                text = self.extract_text_from_content(item)
                if text.strip():
                    sections.append(("root", text))

        if not sections:
            # Если нет секций, весь контент как одна секция
            full_text = self.extract_text_from_content(content_list)
            if full_text.strip():
                sections.append(("root", full_text))

        self.logger.debug(f"Extracted {len(sections)} sections from content")
        return sections