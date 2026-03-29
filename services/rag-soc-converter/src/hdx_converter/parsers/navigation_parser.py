from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import html as html_module
from ..utils.path_resolver import PathResolver
import os

class NavigationParser:
    def __init__(self, path_resolver: PathResolver):
        self.path_resolver = path_resolver
    
    def extract_parent_info(self, soup: BeautifulSoup, html_file: Path) -> Dict:
        """Извлечение информации о родительской статье"""
        parent_info = {
            "title": "",
            "href": "",
            "dc_identifier": ""
        }
        
        parent_link = soup.select_one('div.parentlink a')
        if parent_link:
            parent_info["title"] = parent_link.get_text().strip()
            parent_info["href"] = parent_link.get('href', '')
        
        return parent_info
    
    # parsers/navigation_parser.py - в методе extract_full_hierarchy()
    def extract_full_hierarchy(self, soup: BeautifulSoup, html_file: Path, visited_files=None) -> List[Dict]:
        """Извлечение полной иерархии навигации от корня до родителя"""
        if visited_files is None:
            visited_files = set()

        # Получаем информацию о текущей статье
        current_article = self._get_article_info(soup, html_file)
        if not current_article:
            # Если нет информации о текущей статье - возвращаем сироту
            return [{
                "title": "Orphan Article",
                "dc_identifier": "ORPHAN_ARTICLE",
                "html_filename": "",
                "md_filename": ""
            }]

        # Собираем иерархию родителей
        hierarchy = self._collect_parent_hierarchy(soup, html_file, visited_files)

        # ВАЖНО: Проверяем, действительно ли hierarchy пустая
        # hierarchy может содержать только текущую статью после фильтрации
        if not hierarchy or (len(hierarchy) == 1 and hierarchy[0].get('dc_identifier') == current_article.get('dc_identifier')):
            # Статья сирота - возвращаем структуру для сирот
            return [{
                "title": "Orphan Article",
                "dc_identifier": "ORPHAN_ARTICLE",
                "html_filename": "",
                "md_filename": ""
            }]

        # Фильтруем текущую статью из иерархии
        filtered_hierarchy = []
        for item in hierarchy:
            if item.get('dc_identifier') != current_article.get('dc_identifier'):
                filtered_hierarchy.append(item)

        return filtered_hierarchy

    def _collect_parent_hierarchy(self, soup: BeautifulSoup, html_file: Path,
                                 visited_files: set) -> List[Dict]:
        """Рекурсивный сбор иерархии родителей"""
        # Проверяем, не посещали ли уже этот файл (предотвращение циклов)
        file_key = str(html_file)
        if file_key in visited_files:
            return []

        visited_files.add(file_key)

        # Получаем информацию о текущей статье
        article_info = self._get_article_info(soup, html_file)
        if not article_info:
            return []

        # Ищем родительскую ссылку
        parent_link = soup.select_one('div.parentlink a')
        hierarchy = []

        if parent_link:
            parent_href = parent_link.get('href', '')
            if parent_href:
                try:
                    # Находим родительский файл по оригинальному имени
                    parent_filename = Path(parent_href).name

                    # Ищем родительский файл в той же директории
                    parent_file = html_file.parent / parent_filename
                    if not parent_file.exists():
                        # Пробуем найти в temp_extract_dir
                        parent_file = self.path_resolver.temp_extract_dir / parent_filename

                    if parent_file and parent_file.exists():
                        with open(parent_file, 'r', encoding='utf-8') as f:
                            parent_soup = BeautifulSoup(f.read(), 'html.parser')

                        # Рекурсивно обрабатываем родителя
                        parent_hierarchy = self._collect_parent_hierarchy(parent_soup, parent_file, visited_files)
                        hierarchy.extend(parent_hierarchy)
                except Exception as e:
                    # Не удалось прочитать родительский файл - продолжаем без него
                    pass

        # Добавляем текущую статью в иерархию
        hierarchy.append(article_info)

        return hierarchy
    
    def _get_article_info(self, soup: BeautifulSoup, html_file: Path) -> Dict:
        """Получение информации о статье"""
        title = self._extract_title_from_soup(soup)
        dc_identifier = self._extract_dc_identifier_from_soup(soup)
        
        if not dc_identifier:
            return None
        
        # Генерация имен файлов (упрощенная версия)
        html_filename = html_file.name
        md_filename = f"{self._sanitize_filename(title)}_{dc_identifier}.md"
        
        return {
            "title": title,
            "dc_identifier": dc_identifier,
            "html_filename": html_filename,
            "md_filename": md_filename
        }
    
    def _sanitize_filename(self, filename: str) -> str:
        """Санкционирование имени файла"""
        # Удаляем недопустимые символы
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '-')
        
        # Удаляем множественные дефисы
        while '--' in filename:
            filename = filename.replace('--', '-')
        
        # Обрезаем длинные имена
        if len(filename) > 100:
            filename = filename[:97] + '...'
        
        return filename.strip('-')
    
    def _extract_title_from_soup(self, soup: BeautifulSoup) -> str:
        """Извлечение заголовка из soup"""
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
                    return html_module.unescape(meta['content'].strip())
            else:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    return html_module.unescape(element.get_text().strip())
        
        return ""
    
    def _extract_dc_identifier_from_soup(self, soup: BeautifulSoup) -> str:
        """Извлечение DC.Identifier из soup"""
        meta_id = soup.find('meta', {'name': 'DC.Identifier'})
        if meta_id and meta_id.get('content'):
            return meta_id['content'].strip()
        return ""
    
    def extract_navigation_buttons(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """Извлечение кнопок навигации"""
        nav_buttons = {}
        
        for nav_button in soup.select('div.bottomNavBtn a'):
            href = nav_button.get('href', '')
            text = nav_button.get_text().strip()
            
            if not href:
                continue
            
            if 'previous' in text.lower() or '<' in text:
                nav_type = "previous"
            elif 'next' in text.lower() or '>' in text:
                nav_type = "next"
            else:
                nav_type = "related"
            
            nav_buttons[nav_type] = {
                "text": text,
                "href": href
            }
        
        return nav_buttons
    
    def clean_nav_text(self, text: str) -> str:
        """Очистка текста навигации"""
        return html_module.unescape(text.replace('<', '').replace('>', '').strip())