import re
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from ..writers.file_writer import FileWriter

class MarkdownWriter:
    def __init__(self, config, logger: logging.Logger = None):
        self.config = config
        self.logger = logger
        self.file_writer = FileWriter(config, self.logger)
    
    def convert_to_markdown(self, soup: BeautifulSoup, title: str, content: str,
                           navigation: str, html_file: Path, metadata: dict) -> str:
        """Конвертация в Markdown - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        md_content = "<!--\n"

        if metadata.get("article", {}).get("dc_identifier"):
            md_content += f"Document ID: {metadata['article']['dc_identifier']}\n"

        md_content += f"Source: {html_file.name}\n"

        if metadata.get("article", {}).get("document_type"):
            md_content += f"Type: {metadata['article']['document_type']}\n"

        md_content += "-->\n\n"

        # ИСПРАВЛЕНИЕ: Удаляем блоки кода, содержащие только заголовок статьи
        lines = content.split('\n')
        cleaned_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped.startswith('```'):
                # Проверяем блок кода
                code_block_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    code_block_lines.append(lines[j])
                    j += 1

                if j < len(lines):  # Нашли закрывающий ```
                    code_content = '\n'.join(code_block_lines).strip()
                    # Если в блоке кода только заголовок статьи - пропускаем весь блок
                    if code_content and code_content.lower() == title.lower():
                        i = j + 1  # Пропускаем весь блок кода
                        continue
                    else:
                        cleaned_lines.append(line)
                        i += 1
                else:
                    cleaned_lines.append(line)
                    i += 1
            else:
                cleaned_lines.append(line)
                i += 1

        content = '\n'.join(cleaned_lines)

        # ИСПРАВЛЕНИЕ: Проверяем, начинается ли content с заголовка статьи
        content_lines = content.split('\n')
        has_title_in_content = False

        for i, line in enumerate(content_lines[:5]):
            stripped = line.strip()
            if stripped.startswith('# ') and title.lower() in stripped.lower():
                has_title_in_content = True
                break

        # Добавляем заголовок статьи ТОЛЬКО если его нет в content
        if not has_title_in_content:
            md_content += f"# {title}\n\n"

        # Очистка и конвертация контента
        clean_content = self._clean_md_content(content)
        processed_content = self._process_code_blocks_improved(clean_content)
        md_content += self._convert_txt_to_markdown(processed_content)

        # Добавление навигации
        if navigation:
            md_content += "\n\n## Navigation\n\n"
            clean_nav = self._convert_navigation_to_md(navigation)
            md_content += clean_nav

        return md_content

    def _convert_navigation_to_md(self, navigation: str) -> str:
        """Конвертация навигации в Markdown - ИСПРАВЛЕННАЯ ВЕРСИЯ (пункт 11)"""
        if not navigation:
            return ""

        lines = navigation.split('\n')
        md_lines = []

        for line in lines:
            if line.startswith('---'):
                continue
            match = re.search(r'\[\[(.+?) -> (.+?)\]\]', line)
            if match:
                link_text, target_file = match.groups()
                # ИСПРАВЛЕНИЕ: Убираем .html.md, оставляем только .md
                # Если target_file уже заканчивается на .md, не добавляем еще раз
                if target_file.endswith('.md'):
                    # Уже правильный формат
                    md_link = f"[{link_text}]({target_file})"
                elif target_file.endswith('.html.md'):
                    # Убираем .html
                    clean_target = target_file.replace('.html.md', '.md')
                    md_link = f"[{link_text}]({clean_target})"
                elif target_file.endswith('.html'):
                    # Заменяем .html на .md
                    clean_target = target_file.replace('.html', '.md')
                    md_link = f"[{link_text}]({clean_target})"
                else:
                    # Добавляем .md
                    md_link = f"[{link_text}]({target_file}.md)"
                line = line.replace(f"[[{link_text} -> {target_file}]]", md_link)
            md_lines.append(line)

        return '\n'.join(md_lines).strip()
    
    def _process_code_blocks(self, content: str) -> str:
        """Обработка блоков кода для правильного форматирования"""
        lines = content.split('\n')
        processed_lines = []
        in_code_block = False
        code_block_lines = []
        current_code_block = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Проверяем начало блока кода
            if stripped.startswith('```'):
                if in_code_block:
                    # Закрываем блок кода
                    if current_code_block:
                        # Обрабатываем накопленные строки кода
                        unique_code = self._remove_duplicate_code_lines(current_code_block)
                        processed_lines.append('```')
                        processed_lines.extend(unique_code)
                        processed_lines.append('```')
                    
                    current_code_block = []
                    in_code_block = False
                else:
                    # Открываем новый блок кода
                    in_code_block = True
                
                i += 1
                continue
            
            if in_code_block:
                current_code_block.append(line)
            else:
                # Проверяем, является ли строка командой CLI (простая эвристика)
                if self._looks_like_cli_command(stripped) and not any(x in stripped.lower() for x in ['http://', 'https://', 'www.']):
                    # Начинаем новый блок кода для CLI команды
                    if current_code_block:
                        # Обрабатываем предыдущий блок кода
                        unique_code = self._remove_duplicate_code_lines(current_code_block)
                        processed_lines.append('```')
                        processed_lines.extend(unique_code)
                        processed_lines.append('```')
                        current_code_block = []
                    
                    current_code_block.append(stripped)
                    in_code_block = True
                else:
                    processed_lines.append(line)
            
            i += 1
        
        # Обработка последнего блока кода, если он остался открытым
        if in_code_block and current_code_block:
            unique_code = self._remove_duplicate_code_lines(current_code_block)
            processed_lines.append('```')
            processed_lines.extend(unique_code)
            processed_lines.append('```')
        
        return '\n'.join(processed_lines)

    def _is_cli_command_line(self, line: str, all_lines: list, index: int) -> bool:
        """Определяет, является ли строка CLI командой"""
        if not line or line.startswith(('#', '!', '//', '/*', '*/')):
            return False

        # Паттерны CLI команд из примера
        cli_patterns = [
            r'^system-view$',
            r'^ip\s+vpn-instance\s+',
            r'^ipv[46]-family$',
            r'^tnl-policy\s+',
            r'^[a-z\-]+\s+[a-z\-]+\s+[a-z0-9\-]+(?:\s+[a-z0-9\-]+)*$',
        ]

        line_lower = line.lower()
        for pattern in cli_patterns:
            if re.match(pattern, line_lower):
                return True

        return False

    def _collect_cli_commands(self, lines: list, start_index: int) -> list:
        """Собирает последовательность CLI команд"""
        cli_lines = []
        i = start_index

        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            if self._is_cli_command_line(line, lines, i):
                cli_lines.append(line)
                i += 1
            else:
                break

        return cli_lines

    def _looks_like_cli_command(self, line: str) -> bool:
        """Определяет, похожа ли строка на CLI команду"""
        # Простые эвристики для определения CLI команд
        cli_patterns = [
            r'^[a-z][a-z0-9\-]*(\s+[a-z][a-z0-9\-]*)+$',  # Слова через пробелы
            r'^system-view$',
            r'^ip\s+vpn-instance\s+',
            r'^ipv[46]-family$',
            r'^tnl-policy\s+',
            r'^[a-z\-]+\s+[a-z\-]+\s+[a-z0-9\-]+$',  # Команда с параметрами
        ]
        
        line_lower = line.lower()
        for pattern in cli_patterns:
            if re.match(pattern, line_lower):
                return True
        
        return False
    
    def _remove_duplicate_code_lines(self, lines: List[str]) -> List[str]:
        """Удаление дублирующихся строк кода"""
        if not lines:
            return []
        
        # Удаляем пустые строки в начале и конце
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        # Удаляем дубликаты команд
        seen_commands = set()
        unique_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and stripped not in seen_commands:
                seen_commands.add(stripped)
                unique_lines.append(line)
            elif not stripped:
                unique_lines.append(line)
        
        return unique_lines
    
    def _clean_md_content(self, content: str) -> str:
        """Очистка Markdown контента - УПРОЩЕННАЯ ВЕРСИЯ

        Изменения:
        1. Убрана сложная логика обработки списков через служебные комментарии
        2. Только базовая очистка пустых строк
        """
        if not content:
            return ""
    
        # Убираем множественные пустые строки
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        # Убираем одиночные пустые строки в начале/конце
        result = result.strip()

        return result

    def _convert_txt_to_markdown(self, text: str) -> str:
        """Конвертация текста в Markdown - ДОПОЛНЕННАЯ ВЕРСИЯ

        Добавлено: обработка строк, начинающихся с цифры и точки (упорядоченные списки)
        """
        if not text:
            return ""

        lines = text.split('\n')
        md_lines = []
        in_table = False
        table_lines = []

        for line in lines:
            # Обработка ссылок формата [[текст -> href.html]]
            if '[[' in line and '->' in line and ']]' in line:
                matches = re.findall(r'\[\[(.+?) -> (.+?)\]\]', line)
                for match in matches:
                    link_text, href = match
                    # Конвертируем .html в .md для внутренних ссылок
                    if href.endswith('.html'):
                        md_filename = href.replace('.html', '.md')
                        md_link = f"[{link_text}]({md_filename})"
                    else:
                        md_link = f"[{link_text}]({href})"
                    line = line.replace(f"[[{link_text} -> {href}]]", md_link)

            # Обработка строк, начинающихся с "- " (неупорядоченные списки)
            if line.strip().startswith('- '):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(line)

            # Обработка строк, которые выглядят как элементы упорядоченного списка
            elif re.match(r'^\d+\.\s+.+', line.strip()):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(line)

            # Обработка заголовков
            elif line.startswith('# '):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(line)
            elif line.startswith('## '):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(f"## {line[3:]}")
            elif line.startswith('### '):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(f"### {line[4:]}")
            elif line.startswith('#### '):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(f"#### {line[5:]}")
            elif line.startswith('##### '):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(f"##### {line[6:]}")
            elif line.startswith('###### '):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(f"###### {line[7:]}")

            # Обработка блоков кода
            elif line.strip().startswith('```'):
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False
                md_lines.append(line)

            # Обработка таблиц
            elif ' | ' in line:
                in_table = True
                table_lines.append(line)
            elif line.startswith('---') and '|' not in line and in_table:
                table_lines.append(line)

            # Обработка обычного текста
            else:
                if in_table and table_lines:
                    md_lines.extend(self._format_markdown_table(table_lines))
                    table_lines = []
                    in_table = False

                # Обработка внешних ссылок [external: ...]
                if '[external:' in line:
                    line = re.sub(r'\[external:.+?\]', '', line)

                md_lines.append(line)

        # Обработка последней таблицы
        if in_table and table_lines:
            md_lines.extend(self._format_markdown_table(table_lines))

        result = '\n'.join(md_lines)

        # Очистка форматирования
        result = re.sub(r'\*\*(.+?)\*\*', r'**\1**', result)
        result = re.sub(r'\*(.+?)\*', r'*\1*', result)

        return result
    
    def _format_markdown_table(self, table_lines):
        """Форматирование таблицы в Markdown"""
        if not table_lines:
            return []
        
        formatted_lines = []
        has_header = False
        
        for i, line in enumerate(table_lines):
            if i == 0 and ' | ' in line:
                formatted_lines.append(line)
                parts = line.split(' | ')
                separator = '|' + '|'.join(['---' for _ in parts]) + '|'
                formatted_lines.append(separator)
                has_header = True
            elif line.startswith('---') and has_header:
                continue
            else:
                formatted_lines.append(line)
        
        return formatted_lines

    def save_markdown_file(self, content: str, base_filename: str, 
                          output_dir: Path, title: str = "") -> Optional[Path]:
        """Сохранение Markdown файла без двойного расширения"""
        # Убираем расширение .md если оно уже есть
        if base_filename.lower().endswith('.md'):
            base_filename = base_filename[:-3]

        # Добавляем расширение .md
        filename = f"{base_filename}.md"

        return self.file_writer.save_file(content, filename, "", output_dir, title)

    def _process_code_blocks_improved(self, content: str) -> str:
        """Упрощенная обработка блоков кода

        Логика работы:
        1. Находим все блоки кода, обрамленные ```
        2. Гарантируем, что они имеют правильный формат (``` на отдельных строках)
        3. НЕТ сложной логики определения CLI команд
        4. НЕТ анализа содержимого блоков кода
        """
        lines = content.split('\n')
        processed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Проверяем начало блока кода
            if line.strip().startswith('```'):
                # Начинаем блок кода
                code_block = [line]

                # Ищем конец блока кода
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    code_block.append(lines[j])
                    j += 1

                if j < len(lines):
                    code_block.append(lines[j])  # Добавляем закрывающий ```

                # Гарантируем правильный формат
                if len(code_block) >= 3:
                    # Убираем лишние пробелы вокруг ```
                    code_block[0] = '```'
                    code_block[-1] = '```'

                    # Убираем пустые строки в начале/конце кода
                    code_content = code_block[1:-1]
                    while code_content and not code_content[0].strip():
                        code_content.pop(0)
                    while code_content and not code_content[-1].strip():
                        code_content.pop(-1)

                    # Формируем правильный блок
                    processed_lines.append('```')
                    processed_lines.extend(code_content)
                    processed_lines.append('```')

                i = j + 1 if j < len(lines) else len(lines)
            else:
                processed_lines.append(line)
                i += 1

        return '\n'.join(processed_lines)

    def convert_structured_to_markdown(self, structured_data: Dict[str, Any],
                                         navigation: str, html_file: Path, metadata: dict) -> str:
        """Конвертация структурированных данных в Markdown - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        self.logger.debug(f"=== НАЧАЛО КОНВЕРТАЦИИ STRUCTURED_DATA В MARKDOWN ===")

        md_content = "<!--\n"

        if metadata.get("article", {}).get("dc_identifier"):
            md_content += f"Document ID: {metadata['article']['dc_identifier']}\n"

        md_content += f"Source: {html_file.name}\n"

        if metadata.get("article", {}).get("document_type"):
            md_content += f"Type: {metadata['article']['document_type']}\n"

        md_content += "-->\n\n"

        # Извлекаем заголовок статьи из structured_data
        article_title = structured_data.get("metadata", {}).get("article_title", "")
        if article_title:
            md_content += f"# {article_title}\n\n"
            self.logger.debug(f"Добавлен заголовок статьи: {article_title}")

        # Рекурсивная обработка контента
        def process_element(element, indent_level=0, in_list=False):
            nonlocal md_content
            if isinstance(element, dict):
                element_type = element.get("type")

                if element_type == "section":
                    title = element.get("title", "")
                    content = element.get("content", [])

                    # Определяем уровень заголовка по indent_level
                    if indent_level == 0:
                        header_level = 2
                    else:
                        header_level = min(indent_level + 2, 6)

                    # ИСПРАВЛЕНИЕ: пропускаем секцию навигации, так как она добавляется отдельно
                    if title and title not in ["Навигация", "Navigation"]:
                        md_content += f"\n{'#' * header_level} {title}\n\n"
                        self.logger.debug(f"Добавлена секция: {title} (уровень {header_level})")

                    for item in content:
                        process_element(item, indent_level + 1, False)

                elif element_type == "navigation":
                    # === ИСПРАВЛЕНИЕ: Обработка навигации из structured_data ===
                    content = element.get("content", "")
                    if content:
                        md_content += f"\n\n## Navigation\n\n{content}\n"
                        self.logger.debug(f"Добавлена навигация из structured_data")
                    # === КОНЕЦ ИСПРАВЛЕНИЯ ===

                # === НОВОЕ ИСПРАВЛЕНИЕ: Обработка таблиц ===
                elif element_type == "table":
                    caption = element.get("caption", "")
                    header = element.get("header", [])
                    rows = element.get("rows", [])

                    # Добавляем заголовок таблицы, если есть
                    if caption:
                        md_content += f"**{caption}**\n\n"

                    # Формируем Markdown таблицу
                    if header:
                        md_content += "| " + " | ".join(header) + " |\n"
                        md_content += "|" + "|".join([" --- " for _ in header]) + "|\n"

                        for row in rows:
                            # Убеждаемся, что в строке достаточно элементов
                            row_data = row[:len(header)] if len(row) > len(header) else row + [""] * (len(header) - len(row))
                            md_content += "| " + " | ".join(row_data) + " |\n"

                        md_content += "\n"
                        self.logger.debug(f"Добавлена таблица: caption='{caption}', колонок={len(header)}, строк={len(rows)}")
                # === КОНЕЦ НОВОГО ИСПРАВЛЕНИЯ ===

                elif element_type == "paragraph":
                    content_data = element.get("content", "")
                    if isinstance(content_data, str):
                        md_content += f"{content_data}\n\n"
                    elif isinstance(content_data, list):
                        for item in content_data:
                            process_element(item, indent_level, in_list)
                        md_content += "\n"
                    self.logger.debug(f"Обработан параграф")

                elif element_type == "list":
                    list_type = element.get("list_type", "unordered")
                    items = element.get("items", [])

                    # === ИСПРАВЛЕНИЕ ПРОБЛЕМЫ 4: Добавление переводов строк между элементами списка ===
                    for i, item in enumerate(items):
                        if list_type == "ordered":
                            md_content += f"{'  ' * indent_level}{i + 1}. "
                        else:
                            md_content += f"{'  ' * indent_level}- "

                        process_element(item, indent_level, True)

                        # ДОБАВЛЕНО: Перевод строки после каждого элемента списка
                        md_content += "\n"

                    # ДОБАВЛЕНО: Дополнительный перевод строки после завершения списка
                    if items:
                        md_content += "\n"
                    # === КОНЕЦ ИСПРАВЛЕНИЯ ===

                    self.logger.debug(f"Обработан список ({list_type}): {len(items)} элементов")

                elif element_type == "list_item":
                    content_data = element.get("content", [])
                    text = element.get("text", "")

                    if text:
                        md_content += f"{text}"
                        # === ИСПРАВЛЕНИЕ ПРОБЛЕМЫ 2: Определяем тип следующего элемента ===
                        if content_data:
                            # Проверяем, есть ли среди вложенных элементов параграфы
                            has_paragraphs = any(
                                isinstance(item, dict) and item.get("type") == "paragraph"
                                for item in content_data
                            )

                            if has_paragraphs:
                                # Если есть параграфы, добавляем два перевода строки
                                md_content += "\n\n"
                            else:
                                # Иначе один перевод строки
                                md_content += "\n"

                            # Обрабатываем вложенные элементы с правильными отступами
                            for item in content_data:
                                process_element(item, indent_level, in_list)
                        # ЗАКОНЧИЛИ обработку элемента
                    elif content_data:
                        # === ИСПРАВЛЕНИЕ ПРОБЛЕМЫ 2: Улучшенная логика добавления переводов строк ===
                        first = True
                        for i, item in enumerate(content_data):
                            if not first:
                                # Проверяем текущий и предыдущий элементы
                                prev_item = content_data[i-1] if i > 0 else None
                                current_item = item

                                # Определяем, нужен ли двойной перевод строки
                                need_double_newline = False

                                if isinstance(prev_item, dict) and isinstance(current_item, dict):
                                    prev_type = prev_item.get("type")
                                    current_type = current_item.get("type")

                                    # Добавляем двойной перевод строки для параграфов
                                    if current_type == "paragraph" or prev_type == "paragraph":
                                        need_double_newline = True

                                if need_double_newline:
                                    md_content += "\n\n"
                                else:
                                    md_content += "\n"

                            process_element(item, indent_level, in_list)
                            first = False

                    self.logger.debug(f"Обработан элемент списка")

                elif element_type == "link":
                    text = element.get("text", "")
                    href = element.get("href", "")
                    link_type = element.get("link_type", "")

                    if link_type == "internal" and href.endswith('.html'):
                        # Конвертируем .html в .md для внутренних ссылок
                        md_filename = href.replace('.html', '.md')
                        md_content += f"[{text}]({md_filename})"
                    else:
                        md_content += f"[{text}]({href})"

                    self.logger.debug(f"Обработана ссылка: {text} -> {href}")

                elif element_type == "code_block":
                    content = element.get("content", "")
                    language = element.get("language", "")

                    # === ИСПРАВЛЕНИЕ: Убедимся, что content - строка ===
                    if not isinstance(content, str):
                        content = str(content)

                    md_content += f"\n```{language}\n{content}\n```\n\n"
                    self.logger.debug(f"Обработан code_block (язык: {language}, длина: {len(content)} символов)")

                elif element_type == "image":
                    src = element.get("src", "")
                    alt = element.get("alt", "")

                    md_content += f"\n![{alt}]({src})\n\n"
                    self.logger.debug(f"Обработано изображение: {alt} -> {src}")

                elif element_type == "text":
                    content = element.get("content", "")
                    md_content += content

                # Рекурсивный обход других полей
                for key, value in element.items():
                    if key not in ["type", "content", "title", "text", "href", "link_type",
                                  "navigation_type", "language", "src", "alt", "list_type", "items",
                                  "caption", "header", "rows"]:  # ДОБАВЛЕНО: "caption", "header", "rows"
                        if isinstance(value, (dict, list)):
                            process_element(value, indent_level, in_list)

            elif isinstance(element, list):
                for item in element:
                    process_element(item, indent_level, in_list)

        # Обрабатываем весь контент
        for content_item in structured_data.get("content", []):
            process_element(content_item)

        # === ИСПРАВЛЕНИЕ ПРОБЛЕМЫ 8: Убрано добавление навигации из параметра navigation ===
        # Навигация уже обработана из structured_data
        # === КОНЕЦ ИСПРАВЛЕНИЯ ===

        self.logger.debug(f"=== ЗАВЕРШЕНА КОНВЕРТАЦИИ STRUCTURED_DATA В MARKDOWN ===")
        self.logger.debug(f"Размер MD контента: {len(md_content)} символов")

        return md_content