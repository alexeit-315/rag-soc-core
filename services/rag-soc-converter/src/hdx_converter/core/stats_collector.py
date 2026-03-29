from typing import Dict, List
from datetime import datetime
from ..models.statistics import ConversionStats, ValidationStats, SkippedFileInfo

class StatisticsCollector:
    def __init__(self):
        self.conversion_stats = ConversionStats()
        self.validation_stats = ValidationStats()
        self.skipped_files: List[SkippedFileInfo] = []
        # === ИСПРАВЛЕНИЕ: Флаг наличия ошибок (уже было, проверяем) ===
        self._had_errors = False
        # === КОНЕЦ ИСПРАВЛЕНИЯ ===

    def start_conversion(self):
        """Начало конвертации"""
        self.conversion_stats.start_time = datetime.now()

    def end_conversion(self):
        """Окончание конвертации"""
        self.conversion_stats.end_time = datetime.now()

    def increment_stat(self, stat_name: str, value: int = 1):
        """Увеличение значения статистики"""
        if hasattr(self.conversion_stats, stat_name):
            current = getattr(self.conversion_stats, stat_name)
            setattr(self.conversion_stats, stat_name, current + value)
            # === ИСПРАВЛЕНИЕ: Если увеличиваем errors_encountered, устанавливаем флаг ===
            if stat_name == "errors_encountered" and value > 0:
                self._had_errors = True
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===

    def add_validation_result(self, is_valid: bool, missing_mandatory: List[str],
                             missing_recommended: List[str], missing_optional: List[str]):
        """Добавление результата валидации"""
        self.validation_stats.total_articles += 1

        if is_valid:
            self.validation_stats.valid_articles += 1
        else:
            self.validation_stats.articles_with_errors += 1
            # === ИСПРАВЛЕНИЕ: Устанавливаем флаг ошибок и увеличиваем счетчик ===
            self._had_errors = True
            self.increment_stat("errors_encountered")
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===

        if missing_recommended:
            self.validation_stats.articles_with_warnings += 1

        if missing_optional:
            self.validation_stats.articles_with_info += 1

        # Обновление счетчиков отсутствующих полей
        for field in missing_mandatory:
            field_name = field.split('.')[-1]
            self.validation_stats.missing_mandatory[field_name] = \
                self.validation_stats.missing_mandatory.get(field_name, 0) + 1

        for field in missing_recommended:
            field_name = field.split('.')[-1]
            self.validation_stats.missing_recommended[field_name] = \
                self.validation_stats.missing_recommended.get(field_name, 0) + 1

        for field in missing_optional:
            field_name = field.split('.')[-1]
            self.validation_stats.missing_optional[field_name] = \
                self.validation_stats.missing_optional.get(field_name, 0) + 1

    def add_skipped_file(self, file_path: str, reason: str, details: Dict = None):
        """Добавление информации о пропущенном файле"""
        self.skipped_files.append(SkippedFileInfo(
            file_path=file_path,
            reason=reason,
            details=details
        ))

    # === ИСПРАВЛЕНИЕ: Метод для проверки наличия ошибок (уже было) ===
    def has_errors(self) -> bool:
        """Возвращает True, если были ошибки в процессе конвертации"""
        return self._had_errors or self.conversion_stats.errors_encountered > 0
    # === КОНЕЦ ИСПРАВЛЕНИЯ ===
    
    def get_statistics_summary(self) -> Dict:
        """Получение сводки статистики"""
        return {
            "conversion": self.conversion_stats.model_dump(mode='json'),
            "validation": self.validation_stats.model_dump(mode='json'),
            "skipped_files": len(self.skipped_files),
            "duration": self.conversion_stats.get_duration()
        }