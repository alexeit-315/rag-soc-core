from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re
from ..models.schemas import DocumentType

class MetadataParser:
    @staticmethod
    def extract_metadata_from_html(soup: BeautifulSoup) -> Dict:
        """Извлечение метаданных из HTML"""
        metadata = {
            "document_type": DocumentType.UNKNOWN,
            "language": "",
            "features": [],
            "dc_publisher": "",
            "dc_audience_job": "",
            "prodname": "",
            "version": "",
            "brand": "",
            "addwebmerge": ""
        }
        
        # Тип документа
        meta_type = soup.find('meta', {'name': 'DC.Type'})
        if meta_type and meta_type.get('content'):
            doc_type = meta_type['content'].strip().lower()
            if 'cliref' in doc_type:
                metadata["document_type"] = DocumentType.CLI_COMMAND
            elif 'task' in doc_type:
                metadata["document_type"] = DocumentType.CONFIGURATION_GUIDE
            elif 'concept' in doc_type:
                metadata["document_type"] = DocumentType.CONCEPT
        
        # Язык
        meta_lang = soup.find('meta', {'name': 'DC.Language'})
        if meta_lang and meta_lang.get('content'):
            metadata["language"] = meta_lang['content'].strip()
        
        # Особенности (features)
        feature_metas = soup.find_all('meta', {'name': 'featurename'})
        for feature_meta in feature_metas:
            if feature_meta.get('content'):
                feature_name = feature_meta['content'].strip()
                if feature_name not in metadata["features"]:
                    metadata["features"].append(feature_name)
        
        # Дополнительные метаданные
        meta_fields = {
            'DC.Publisher': 'dc_publisher',
            'DC.Audience.Job': 'dc_audience_job',
            'prodname': 'prodname',
            'version': 'version',
            'brand': 'brand',
            'AddWebMerge': 'addwebmerge'
        }
        
        for meta_name, field_name in meta_fields.items():
            meta = soup.find('meta', {'name': meta_name})
            if meta and meta.get('content'):
                metadata[field_name] = meta['content'].strip()
        
        return metadata
    
    @staticmethod
    def extract_dc_identifier(soup: BeautifulSoup) -> Optional[str]:
        """Извлечение DC.Identifier"""
        meta_id = soup.find('meta', {'name': 'DC.Identifier'})
        if meta_id and meta_id.get('content'):
            return meta_id['content'].strip()
        return None
    
    @staticmethod
    @staticmethod
    def extract_firmware_versions(content: str) -> List[str]:
        """Извлечение версий прошивки из текста - ДОПОЛНИТЕЛЬНО ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        versions = []
        patterns = [
            r'V\d+R\d+C\d+',           # Основной формат VxxxRxxxCxx
            r'V\d+R\d+C\d+SPC\d+',     # С патчами VxxxRxxxCxxSPCxxx
            # УБРАН ПАТТЕРН: r'\d+\.\d+\.\d+', который ловил IP-адреса
            # Добавлены более специфичные паттерны
            r'V\d{3}R\d{3}C\d{2,3}',   # Точный формат VxxxRxxxCxx
            r'V\d{3}R\d{3}C\d{2,3}SPC\d{1,3}',  # С патчами
            r'V\d{3}R\d{3}',           # Без C-части VxxxRxxx
            r'V\d{3}R\d{3}C\d{2,3}SPH\d{1,3}',  # С hotfix
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            versions.extend(matches)

        # ФИЛЬТРАЦИЯ IP-адресов и номеров пунктов (дополнительная защита)
        filtered_versions = []
        for version in versions:
            # Проверяем, что это не IP-адрес (формат x.x.x.x)
            if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', version):
                continue

            # Проверяем, что это не номер пункта (формат 10.1.1, 10.0.0 и т.д.)
            if re.match(r'^10\.\d+\.\d+$', version):
                continue
            if re.match(r'^255\.255\.255$', version):
                continue
            if re.match(r'^0\.0\.0$', version):
                continue

            # Проверяем, что начинается с V (версия прошивки)
            if version.upper().startswith('V'):
                filtered_versions.append(version)

        return list(set(filtered_versions))
    
    @staticmethod
    def extract_platforms(content: str) -> List[str]:
        """Извлечение платформ из текста"""
        platforms = []
        patterns = [
            r'USG\d+[A-Z\-]*',
            r'CE\d+[A-Z]*',
            r'S\d+[A-Z]*',
            r'AR\d+[A-Z]*',
            r'NetEngine\d+[A-Z]*',
            r'Atlas\d+[A-Z]*',
            r'HiSecEngine\d+[A-Z\-]*',
            r'CloudEngine\d+[A-Z]*',
            r'AirEngine\d+[A-Z]*',
            r'USG\d+[A-Z]+-E\d+-[A-Z]+',  # USG6000F-E06-D
            r'USG\d+[A-Z]+-[A-Z]+',       # USG6510F-DPL
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # === ИСПРАВЛЕНИЕ: Фильтруем ложные срабатывания ===
                # Пропускаем очень короткие (менее 4 символов) совпадения
                if len(match) < 4:
                    continue
                # Пропускаем если это "s1" или подобные
                if match.upper().startswith('S') and match[1:].isdigit() and len(match) < 4:
                    continue
                platforms.append(match)
                # === КОНЕЦ ИСПРАВЛЕНИЯ ===
        
        return list(set(platforms))