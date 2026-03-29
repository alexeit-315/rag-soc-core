#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logger for index builder with container support
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import os


class IndexBuilderLogger:
    def __init__(self, name: str = "IndexBuilder", verbose_level: int = 2, log_file: Optional[Path] = None):
        """
        Инициализация логгера

        Args:
            name: имя логгера
            verbose_level: уровень детализации (0-3)
                0: только ошибки
                1: warnings и выше
                2: info и выше (по умолчанию)
                3: debug
            log_file: путь к файлу лога (опционально)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # Определяем уровень логирования на основе verbose_level
        if verbose_level == 0:
            console_level = logging.ERROR
            file_level = logging.ERROR
        elif verbose_level == 1:
            console_level = logging.WARNING
            file_level = logging.INFO
        elif verbose_level == 2:
            console_level = logging.INFO
            file_level = logging.INFO
        else:  # verbose_level == 3
            console_level = logging.DEBUG
            file_level = logging.DEBUG

        # Форматтер для логов (в контейнере добавляем префикс)
        is_container = os.path.exists('/.dockerenv')

        if is_container:
            formatter = logging.Formatter(
                '%(asctime)s - [CONTAINER] - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        # В контейнере логируем в stdout/stderr (для сбора Docker logs)
        if is_container:
            # В контейнере используем stdout для info и выше
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setLevel(logging.INFO)
            stdout_handler.setFormatter(formatter)
            self.logger.addHandler(stdout_handler)

            # stderr для ошибок
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setLevel(logging.WARNING)
            stderr_handler.setFormatter(formatter)
            self.logger.addHandler(stderr_handler)
        else:
            # В консоли используем стандартные обработчики
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(console_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # Прогресс в stdout
            progress_handler = logging.StreamHandler(sys.stdout)
            progress_handler.setLevel(logging.INFO)
            progress_handler.setFormatter(formatter)
            self.logger.addHandler(progress_handler)

        # Файловый handler (полный лог) - работает везде
        if log_file:
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(file_level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"Could not create log file {log_file}: {e}")

    def get_logger(self) -> logging.Logger:
        return self.logger

    @staticmethod
    def setup_logging(verbose_level: int = 2, log_dir: Optional[Path] = None) -> logging.Logger:
        """Удобный метод для быстрой настройки логирования"""
        log_file = None
        if log_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"index_builder_{timestamp}.log"

        return IndexBuilderLogger("IndexBuilder", verbose_level, log_file).get_logger()