from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from ..utils.path_resolver import PathResolver

class LinkProcessor:
    def __init__(self, path_resolver: PathResolver):
        self.path_resolver = path_resolver
    
    def is_internal_link(self, href: str, source_file: Path) -> bool:
        """Проверка, является ли ссылка внутренней"""
        if not href:
            return False
        
        if href.startswith('#') or href.startswith(('http://', 'https://')):
            return False
        
        if href.lower().startswith('cmdqueryname='):
            return False
        
        if href.lower().endswith('.html'):
            return True
        
        return False
    
    def extract_all_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Извлечение всех ссылок из документа"""
        links = []
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            text = a_tag.get_text().strip()
            if href:
                links.append({
                    'text': text,
                    'href': href,
                    'is_internal': self.is_internal_link(href, Path(""))
                })
        return links