#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Index Builder - Creates vector indices from JSON documentation for RAG bots
"""

__version__ = "1.3.0"
__author__ = "Your Name"
__year__ = "2026"

from .core.index_builder import IndexBuilder
from .models.schemas import ChunkMetadata, ProcessingStats