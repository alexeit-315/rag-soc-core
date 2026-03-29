# utils/logger.py
import logging
from pathlib import Path
from ..models.config import ConverterConfig

class HDXLogger:
    def __init__(self, config: ConverterConfig, verbose_level: int = 2):
        self.config = config
        self.verbose_level = verbose_level
        self.logger = logging.getLogger('HDXConverter')
        self.setup_logging()

    def setup_logging(self):
        # Устанавливаем уровень логгера на DEBUG, чтобы все сообщения обрабатывались
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # Очищаем существующие обработчики

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Файловый обработчик - уровень зависит от verbose_level
        log_file = self.config.output_dir / self.config.log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)

        # Настройка уровня файлового лога согласно verbose_level
        if self.verbose_level == 0:  # silent
            file_handler.setLevel(logging.ERROR)
        elif self.verbose_level == 1:  # short
            file_handler.setLevel(logging.WARNING)
        elif self.verbose_level == 2:  # normal
            file_handler.setLevel(logging.INFO)
        else:  # debug (v3)
            file_handler.setLevel(logging.DEBUG)

        # Консольный обработчик - уровень зависит от verbose_level
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        if self.verbose_level == 0:  # silent - ничего в консоль
            console_handler.setLevel(logging.CRITICAL + 1)  # Уровень выше CRITICAL - ничего не выводит
        else:  # short, normal, debug - только ERROR в консоль
            console_handler.setLevel(logging.ERROR)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.propagate = False
    
    def get_logger(self):
        return self.logger
    
    def close(self):
        for handler in self.logger.handlers:
            handler.close()