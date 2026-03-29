from bs4 import BeautifulSoup
import re
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any
import html as html_module
from ..models.schemas import SectionType

class HTMLParser:
    @staticmethod
    def extract_title(soup: BeautifulSoup, html_file: Path) -> str:
        """Извлечение заголовка из HTML"""
        title_selectors = [
            'title',
            'h1.topicTitle-h1',
            'h1',
            '.topicTitle-h1',
            'meta[name="DC.Title"]'
        ]

        for selector in title_selectors:
            if selector.startswith('meta'):
                meta = soup.find('meta', {'name': 'DC.Title'})
                if meta and meta.get('content'):
                    title = html_module.unescape(meta['content'].strip())
                    return title
            else:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    title = html_module.unescape(element.get_text().strip())
                    return title

        return html_file.stem

    @staticmethod
    def find_main_content(soup: BeautifulSoup) -> BeautifulSoup:
        """Поиск основного контента"""
        content_selectors = [
            'div.articleBoxWithoutHead',
            'article',
            'main',
            '.content',
            'body'
        ]

        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                return content_element

        return soup.find('body') or soup

    @staticmethod
    def clean_html_content(soup: BeautifulSoup) -> BeautifulSoup:
        """Очистка HTML от ненужных элементов

        НЕ удаляем footer навигацию, так как она нужна для извлечения ссылок
        НЕ удаляем <pre> теги, так как они содержат CLI команды
        """
        for element in soup.find_all(['script', 'style', 'nav', 'header']):
            element.decompose()

        # Удаляем только copyright, но оставляем навигацию и блоки кода
        for element in soup.find_all(['div.copyrightBottomBar',
                                      'div.copyrightBottomBar_responsive']):
            element.decompose()

        return soup

    @staticmethod
    def extract_table_content(table_element) -> str:
        """Извлечение содержимого таблицы"""
        try:
            rows = table_element.find_all('tr')
            if not rows:
                return ""

            table_lines = []
            seen_rows = set()

            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                row_data = []

                for cell in cells:
                    cell_text = cell.get_text().strip()
                    cell_text = re.sub(r'\s+', ' ', cell_text)
                    row_data.append(cell_text)

                if row_data:
                    row_key = '|'.join(row_data)
                    if row_key in seen_rows:
                        continue
                    seen_rows.add(row_key)

                    is_header = any(cell.name == 'th' for cell in cells)
                    table_line = " | ".join(row_data)
                    table_lines.append(table_line)

                    if is_header and i == 0:
                        separator = "-" * len(table_line)
                        table_lines.append(separator)

            return "\n".join(table_lines)

        except Exception as e:
            return table_element.get_text().strip()

    @staticmethod
    def extract_all_images(soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Извлечение всех изображений"""
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                alt = img.get('alt', '')
                title = img.get('title', '')
                images.append({
                    'src': src,
                    'alt': alt,
                    'title': title
                })
        return images

    @staticmethod
    def determine_section_type(element) -> SectionType:
        """Определение типа раздела"""
        class_attr = element.get('class', [])
        if isinstance(class_attr, list):
            class_attr = ' '.join(class_attr)

        if 'clifunc' in class_attr:
            return SectionType.FUNCTION
        elif 'cliformat' in class_attr:
            return SectionType.FORMAT
        elif 'cliparam' in class_attr:
            return SectionType.PARAMETERS
        elif 'cliview' in class_attr:
            return SectionType.VIEWS
        elif 'example' in class_attr:
            return SectionType.EXAMPLE
        else:
            return SectionType.CONTENT

    @staticmethod
    def process_html_list(list_element) -> str:
        """Обработка HTML списка - УЛУЧШЕННАЯ ВЕРСИЯ

        Изменения:
        1. Сохраняем переносы строк между элементами
        2. Добавляем базовые маркеры списков
        3. Убраны служебные комментарии
        """
        if not list_element:
            return ""

        # Простое текстовое представление, но с сохранением переносов
        list_text = list_element.get_text(separator='\n', strip=True)

        if not list_text:
            return ""

        # Добавляем маркеры списка
        lines = list_text.split('\n')
        result_lines = []

        for line in lines:
            if line.strip():
                if list_element.name == 'ol':
                    # Для упорядоченных списков - просто текст (нумерацию добавит markdown-конвертер)
                    result_lines.append(line)
                else:
                    # Для неупорядоченных - добавляем дефис
                    result_lines.append(f"- {line}")

        if result_lines:
            return "\n" + "\n".join(result_lines) + "\n"

        return ""