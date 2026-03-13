from typing import List, Dict, Any
import logging
from ..models.schemas import ArticleMetadata, Validation
from ..models.config import ConverterConfig

class MetadataValidator:
    def __init__(self, config: ConverterConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def validate_metadata(self, metadata: ArticleMetadata) -> Validation:
        """Валидация метаданных статьи"""
        self.logger.debug(f"=== VALIDATE_METADATA НАЧАЛО ===")

        validation = Validation()

        # Проверка обязательных полей
        self.logger.debug(f"Проверка mandatory_fields ({len(self.config.mandatory_fields)} полей):")
        missing_mandatory = self._check_mandatory_fields(metadata)
        self.logger.debug(f"  Найдено missing_mandatory: {missing_mandatory}")

        # Проверка рекомендуемых полей (исключаем external_links)
        recommended_to_check = [
            field for field in self.config.recommended_fields
            if field != "relations.external_links"
        ]

        self.logger.debug(f"Проверка recommended_fields ({len(recommended_to_check)} полей, исключая external_links):")
        missing_recommended = []
        for field_path in recommended_to_check:
            value = self._get_nested_value(metadata, field_path)
            self.logger.debug(f"  Поле '{field_path}': значение={repr(value)[:50] if value else 'None/Empty'}")
            if not value:
                missing_recommended.append(field_path)
                self.logger.debug(f"    -> ДОБАВЛЕНО В missing_recommended")

        self.logger.debug(f"  Найдено missing_recommended: {missing_recommended}")

        # Проверка опциональных полей
        self.logger.debug(f"Проверка optional_fields ({len(self.config.optional_fields)} полей):")
        missing_optional = self._check_optional_fields(metadata)
        self.logger.debug(f"  Найдено missing_optional: {missing_optional}")

        # Только обязательные поля влияют на mandatory
        all_missing_mandatory = missing_mandatory
        self.logger.debug(f"all_missing_mandatory = mandatory = {all_missing_mandatory}")

        # Рекомендуемые сохраняются отдельно
        if all_missing_mandatory:
            validation.missing_fields.mandatory = all_missing_mandatory
            self.logger.debug(f"Установлено validation.missing_fields.mandatory: {all_missing_mandatory}")
            # === ИСПРАВЛЕНИЕ: Логирование ошибок валидации на уровне ERROR ===
            self.logger.error(f"Статья '{metadata.article.get('title', 'Unknown')}' невалидна: отсутствуют обязательные поля: {', '.join(all_missing_mandatory)}")
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===

        if missing_recommended:
            validation.missing_fields.recommended = missing_recommended
            self.logger.debug(f"Установлено validation.missing_fields.recommended: {missing_recommended}")
            # === ИСПРАВЛЕНИЕ: Логирование предупреждений на уровне WARNING ===
            self.logger.warning(f"Статья '{metadata.article.get('title', 'Unknown')}' имеет предупреждения: отсутствуют рекомендуемые поля: {', '.join(missing_recommended)}")
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===

        if missing_optional:
            validation.missing_fields.optional = missing_optional
            self.logger.debug(f"Установлено validation.missing_fields.optional: {missing_optional}")

        # Проверка дополнительных ошибок
        errors = self._check_for_errors(metadata)
        if errors:
            validation.errors = errors
            self.logger.debug(f"Найдены errors: {errors}")

        # Определение валидности
        validation.is_valid = len(all_missing_mandatory) == 0 and len(errors) == 0
        self.logger.debug(f"validation.is_valid = {validation.is_valid} (missing_mandatory={len(all_missing_mandatory)}, errors={len(errors)})")

        # Предупреждения для сиротских статей
        hierarchy = metadata.article.get("hierarchy", [])
        if hierarchy and len(hierarchy) == 1 and hierarchy[0].get("dc_identifier") == "ORPHAN_ARTICLE":
            validation.warnings.append("Article has no parent in navigation hierarchy (orphan article)")
            self.logger.debug(f"Добавлено предупреждение: сиротская статья")
            # === ИСПРАВЛЕНИЕ: Предупреждение для -v1 ===
            self.logger.warning(f"Статья '{metadata.article.get('title', 'Unknown')}' является сиротской (нет родителя в иерархии)")
            # === КОНЕЦ ИСПРАВЛЕНИЯ ===

        # Предупреждения для отсутствующих рекомендуемых полей
        if missing_recommended:
            warning_msg = f"Missing recommended fields: {', '.join(missing_recommended)}"
            validation.warnings.append(warning_msg)
            self.logger.debug(f"Добавлено предупреждение: {warning_msg}")

        # Предупреждение для отсутствующих external_links
        external_links = metadata.relations.external_links if metadata.relations else []
        if not external_links:
            validation.warnings.append("No external links found")
            self.logger.debug(f"Добавлено предупреждение: нет external links")

        self.logger.debug(f"=== VALIDATE_METADATA КОНЕЦ: valid={validation.is_valid}, missing_mandatory={len(all_missing_mandatory)} ===")
        return validation

    def _check_mandatory_fields(self, metadata: ArticleMetadata) -> List[str]:
        """Проверка обязательных полей"""
        missing = []

        self.logger.debug(f"=== _check_mandatory_fields: проверка {len(self.config.mandatory_fields)} полей ===")

        for field_path in self.config.mandatory_fields:
            value = self._get_nested_value(metadata, field_path)

            # === ДОБАВЛЕНО: Логирование для каждого поля ===
            if value is None:
                self.logger.debug(f"  Поле '{field_path}': значение=None -> ДОБАВЛЯЕМ В MISSING")
                missing.append(field_path)
            elif isinstance(value, bool):
                self.logger.debug(f"  Поле '{field_path}': boolean значение={value}")
                # Boolean False - это валидное значение, не добавляем в missing
                if value is False:
                    self.logger.debug(f"    Boolean False - НЕ добавляем в missing")
            elif isinstance(value, (list, dict, str)):
                if not value:
                    self.logger.debug(f"  Поле '{field_path}': пустой {type(value).__name__} -> ДОБАВЛЯЕМ В MISSING")
                    missing.append(field_path)
                else:
                    self.logger.debug(f"  Поле '{field_path}': найдено, тип={type(value)}, значение preview={repr(value)[:50]}")
            else:
                self.logger.debug(f"  Поле '{field_path}': найдено, тип={type(value)}")

        self.logger.debug(f"=== _check_mandatory_fields КОНЕЦ: найдено {len(missing)} missing полей ===")
        return missing

    def _check_recommended_fields(self, metadata: ArticleMetadata) -> List[str]:
        """Проверка рекомендуемых полей"""
        missing = []

        # === ИЗМЕНЕНИЕ: Обновлено имя поля и логика ===
        for field_path in self.config.recommended_fields:
            if field_path == "relations.external_links":
                continue  # Пропускаем external_links - не обязательные
            value = self._get_nested_value(metadata, field_path)
            if not value:
                missing.append(field_path)

        return missing

    def _check_optional_fields(self, metadata: ArticleMetadata) -> List[str]:
        """Проверка опциональных полей"""
        missing = []

        # === ИЗМЕНЕНИЕ: Обновлено имя поля ===
        for field_path in self.config.optional_fields:
            value = self._get_nested_value(metadata, field_path)
            if not value:
                missing.append(field_path)
        
        return missing
    
    def _check_for_errors(self, metadata: ArticleMetadata) -> List[str]:
        """Проверка на ошибки"""
        errors = []
        
        # Проверка длины DC.Identifier
        dc_identifier = metadata.article.get("dc_identifier", "")
        if dc_identifier and len(dc_identifier) < 5:
            errors.append("dc_identifier слишком короткий")
        
        # Проверка иерархии на дубликаты заголовков
        hierarchy = metadata.article.get("hierarchy", [])
        titles = [item.get("title", "") for item in hierarchy if item.get("title")]
        if len(titles) != len(set(titles)):
            errors.append("article.hierarchy contains duplicate titles")
        
        return errors
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Получение значения по вложенному пути"""
        self.logger.debug(f"=== _get_nested_value НАЧАЛО: путь='{path}' ===")
        self.logger.debug(f"  Тип obj: {type(obj)}")

        keys = path.split('.')
        current = obj

        for i, key in enumerate(keys):
            self.logger.debug(f"  Шаг {i+1}/{len(keys)}: ключ='{key}', текущий тип: {type(current)}")

            # === ДОБАВЛЕНО: Логирование для Pydantic моделей ===
            if hasattr(current, 'model_dump'):
                self.logger.debug(f"    Объект является Pydantic моделью: {current.__class__.__name__}")
                data = current.model_dump()
                self.logger.debug(f"    model_dump() ключи: {list(data.keys())}")

            # Сначала пробуем получить как атрибут
            if hasattr(current, key):
                value = getattr(current, key)
                self.logger.debug(f"    Найден как атрибут: значение={repr(value)[:100]}..., тип={type(value)}")
                current = value
            # Потом как ключ словаря
            elif isinstance(current, dict) and key in current:
                value = current[key]
                self.logger.debug(f"    Найден в dict: значение={repr(value)[:100]}..., тип={type(value)}")
                current = value
            else:
                self.logger.debug(f"    НЕ НАЙДЕН: нет атрибута '{key}' в объекте типа {type(current)}")
                if isinstance(current, dict):
                    self.logger.debug(f"    Доступные ключи в dict: {list(current.keys())}")
                elif hasattr(current, '__dict__'):
                    self.logger.debug(f"    Доступные атрибуты: {[a for a in dir(current) if not a.startswith('_')][:10]}...")
                self.logger.debug(f"=== _get_nested_value КОНЕЦ: возвращаю None для '{path}' ===")
                return None

            # Проверка пустых значений
            if current is None:
                self.logger.debug(f"    Значение None для ключа '{key}'")
                self.logger.debug(f"=== _get_nested_value КОНЕЦ: возвращаю None (None value) ===")
                return None
            elif isinstance(current, (list, dict)) and not current:
                self.logger.debug(f"    Пустой {type(current).__name__} для ключа '{key}'")
                self.logger.debug(f"=== _get_nested_value КОНЕЦ: возвращаю None (empty container) ===")
                return None
            elif isinstance(current, str) and not current.strip():
                self.logger.debug(f"    Пустая строка для ключа '{key}'")
                self.logger.debug(f"=== _get_nested_value КОНЕЦ: возвращаю None (empty string) ===")
                return None

            # === ДОБАВЛЕНО: Специальная проверка для boolean значений ===
            if isinstance(current, bool):
                self.logger.debug(f"    Boolean значение: {current}")
                # Boolean значения должны возвращаться как есть, даже если False
                # Не возвращаем None для False!

        self.logger.debug(f"=== _get_nested_value КОНЕЦ: возвращаю значение для '{path}': {repr(current)[:100]}..., тип={type(current)} ===")
        return current