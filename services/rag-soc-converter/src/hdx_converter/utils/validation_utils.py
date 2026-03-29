from typing import List, Dict, Any
import re

class ValidationUtils:
    @staticmethod
    def validate_dc_identifier(dc_identifier: str) -> bool:
        """Валидация DC.Identifier"""
        if not dc_identifier:
            return False
        if len(dc_identifier) < 5:
            return False
        # Можно добавить дополнительные проверки формата
        return True
    
    @staticmethod
    def check_for_duplicates(items: List[Any], key: str = "title") -> List[str]:
        """Поиск дубликатов в списке"""
        seen = set()
        duplicates = []
        
        for item in items:
            value = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
            if value in seen:
                duplicates.append(value)
            else:
                seen.add(value)
        
        return duplicates
    
    @staticmethod
    def validate_filename(filename: str, max_length: int = 128) -> Dict[str, Any]:
        """Валидация имени файла"""
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        if len(filename) > max_length:
            result["is_valid"] = False
            result["errors"].append(f"Filename too long ({len(filename)} > {max_length})")
        
        invalid_chars = re.findall(r'[<>:"/\\|?*]', filename)
        if invalid_chars:
            result["is_valid"] = False
            result["errors"].append(f"Invalid characters in filename: {set(invalid_chars)}")
        
        if filename.startswith('.') or filename.endswith('.'):
            result["warnings"].append("Filename starts or ends with dot")
        
        return result