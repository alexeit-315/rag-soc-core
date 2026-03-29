#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Multi-pass cleaner для техдоков

Что делает:
 - читает входную папку с markdown/text/doc-файлами
 - очищает каждый файл
 - сохраняет очищенный результат в выходную папку
 - печатает логи выполнения
 - печатает финальную статистику
"""

import os
import re
import sys
import time
from typing import List, Tuple


# ==============================
# MultiPass Cleaner Core
# ==============================
class MultiPassCleaner:
    def __init__(self):
        pass

    def run_all_passes(self, text: str) -> str:
        original_len = len(text)

        x = text
        x = self._normalize_unicode(x)
        x = self._fix_pdf_artifacts(x)
        x = self._preserve_code_blocks(x)
        x = self._strip_html(x)
        x = self._normalize_whitespace(x)
        x = self._fix_broken_lists(x)

        return x

    def _normalize_unicode(self, text: str) -> str:
        rep = {
            "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
            "\u201c": '"', "\u201d": '"', "\ufb01": "fi", "\ufb02": "fl"
        }
        for k, v in rep.items():
            text = text.replace(k, v)
        return text

    def _fix_pdf_artifacts(self, text: str) -> str:
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        return text

    def _preserve_code_blocks(self, text: str) -> str:
        text = re.sub(r'```+', '```', text)
        return text

    def _strip_html(self, text: str) -> str:
        text = re.sub(r'<head>.*?</head>', ' ', text, flags=re.S | re.I)
        text = re.sub(r'<script.*?>.*?</script>', ' ', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _fix_broken_lists(self, text: str) -> str:
        text = re.sub(r'(\n|\s)-\s+', ' - ', text)
        return text


# ==============================
# Markdown Section Extractor
# ==============================
def extract_sections_from_markdown(text: str) -> List[Tuple[str, str]]:
    lines = text.splitlines()
    sections = []
    current_title = "root"
    current_lines = []

    for ln in lines:
        m = re.match(r'^\s{0,3}(#{1,6})\s+(.*)', ln)
        if m:
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(ln)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    if not sections:
        return [("root", text)]

    return sections


# ==============================
# Runner
# ==============================
def clean_folder(input_folder: str, output_folder: str):
    print(f"\n=== Multi-pass cleaner ===")
    print(f"⏳ Начинаю обработку...")
    print(f"📂 Входная папка: {input_folder}")
    print(f"📁 Выходная папка: {output_folder}")

    t0 = time.time()
    cleaner = MultiPassCleaner()

    if not os.path.exists(input_folder):
        print(f"❌ Ошибка: входная папка не существует: {input_folder}")
        sys.exit(1)

    os.makedirs(output_folder, exist_ok=True)

    processed = 0
    errors = 0
    total_chars_before = 0
    total_chars_after = 0

    for root, _, files in os.walk(input_folder):
        for fname in files:
            if not fname.lower().endswith((".md", ".txt")):
                continue

            in_path = os.path.join(root, fname)
            rel_path = os.path.relpath(in_path, input_folder)
            out_path = os.path.join(output_folder, rel_path)

            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            try:
                print(f"➡️  Обрабатываю: {rel_path}")
                with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

                total_chars_before += len(text)
                cleaned = cleaner.run_all_passes(text)
                total_chars_after += len(cleaned)

                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(cleaned)

                processed += 1

            except Exception as e:
                print(f"❌ Ошибка при обработке {rel_path}: {e}")
                errors += 1

    dt = time.time() - t0
    print("\n=== ✔ Статистика ===")
    print(f"Файлов обработано:      {processed}")
    print(f"Ошибок:                 {errors}")
    print(f"Символов ДО:            {total_chars_before}")
    print(f"Символов ПОСЛЕ:         {total_chars_after}")
    print(f"Экономия:               {total_chars_before - total_chars_after}")
    print(f"⏱ Время выполнения:     {dt:.2f} сек")

    if errors == 0:
        print("🎉 УСПЕХ: Все файлы обработаны.")
    else:
        print("⚠️ Завершено с ошибками.")


# ==============================
# CLI
# ==============================
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование:")
        print("   python multi_pass_cleaner.py <input_folder> <output_folder>")
        sys.exit(1)

    clean_folder(sys.argv[1], sys.argv[2])
