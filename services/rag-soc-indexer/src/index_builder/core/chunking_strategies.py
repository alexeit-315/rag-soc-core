#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chunking strategies for document processing
"""

from typing import List, Tuple, Dict, Any, Optional
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChunkingStrategy:
    """Base class for chunking strategies"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Chunk text and return list of (chunk_text, chunk_metadata)"""
        raise NotImplementedError


class SizeBasedChunking(ChunkingStrategy):
    """Chunk by size using RecursiveCharacterTextSplitter"""

    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 150, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; "]
        )

    def chunk(self, text: str, base_metadata: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Разбивает текст на чанки по размеру"""
        docs = self.splitter.create_documents([text])
        result = []

        for idx, doc in enumerate(docs):
            chunk_text = doc.page_content.strip()
            if not chunk_text:
                continue

            # Копируем базовые метаданные и добавляем специфичные для чанка
            chunk_metadata = base_metadata.copy()
            chunk_metadata.update({
                "chunk_id": f"{base_metadata.get('chunk_id', '0')}_{idx}",
                "start": doc.metadata.get("start_index", 0),
                "length": len(chunk_text)
            })

            result.append((chunk_text, chunk_metadata))

        return result


class StructureBasedChunking(ChunkingStrategy):
    """Chunk by document structure (sections from JSON)"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)

    def chunk(self, sections: List[Tuple[str, str]], base_metadata: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Создает чанки по секциям

        Args:
            sections: список (section_title, section_text)
            base_metadata: базовые метаданные для всех чанков
        """
        result = []

        for sec_idx, (section_title, section_text) in enumerate(sections):
            if not section_text.strip():
                continue

            # Копируем базовые метаданные и добавляем специфичные для секции
            chunk_metadata = base_metadata.copy()
            chunk_metadata.update({
                "section": section_title,
                "chunk_id": f"{sec_idx}",
                "start": 0,
                "length": len(section_text)
            })

            result.append((section_text, chunk_metadata))

        return result