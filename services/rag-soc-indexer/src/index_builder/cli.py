#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command line interface for index builder with GPU support
"""

import argparse
from pathlib import Path
import sys
import os
import torch


def get_env_path(env_var: str, default: str) -> str:
    """Получает путь из переменной окружения"""
    value = os.environ.get(env_var, default)
    
    if os.path.exists(value) or os.path.exists(os.path.dirname(value)):
        return value
    
    if os.path.exists('/.dockerenv'):
        Path(value).mkdir(parents=True, exist_ok=True)
        return value
    
    return value


def detect_environment() -> str:
    """Определяет среду выполнения"""
    if os.path.exists('/.dockerenv'):
        return 'container'
    
    if os.environ.get('KUBERNETES_SERVICE_HOST') or os.environ.get('CONTAINER'):
        return 'container'
    
    return 'console'


def check_gpu():
    """Проверяет доступность GPU и выводит информацию"""
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        print(f"🎮 Найдено GPU: {gpu_count}")
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
            print(f"   {i}: {gpu_name} ({gpu_memory:.1f} GB)")
        return True
    else:
        print("💻 GPU не найден, будет использован CPU")
        return False


def setup_container_paths(args) -> argparse.Namespace:
    """Настраивает пути для контейнерной среды"""
    Path(args.source_folder).mkdir(parents=True, exist_ok=True)
    if args.meta_folder:
        Path(args.meta_folder).mkdir(parents=True, exist_ok=True)
    Path(args.persist_dir).mkdir(parents=True, exist_ok=True)
    
    if args.model_path:
        Path(args.model_path).parent.mkdir(parents=True, exist_ok=True)
    
    if args.log_dir:
        Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    
    return args


def main():
    environment = detect_environment()
    
    # Проверяем GPU при запуске
    has_gpu = check_gpu()
    
    parser = argparse.ArgumentParser(
        description='Build vector index from JSON documentation files with GPU support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Environment: {environment}
GPU Available: {'✅' if has_gpu else '❌'}

Two folders structure:
  --source-folder  : JSON files with article CONTENT (from json_data/)
  --meta-folder    : JSON files with article METADATA (from meta_data/)

Environment variables:
  SOURCE_JSON_FOLDER  - source folder with JSON content files
  META_JSON_FOLDER    - folder with JSON metadata files
  PERSIST_DIR         - folder for vector index
  MODEL_PATH          - path to local embedding model
  LOG_DIR             - directory for log files
  CUDA_VISIBLE_DEVICES - select specific GPU (e.g., "0" or "0,1")

Examples:
  # Автоматический выбор устройства
  python -m index_builder.cli --source-folder ./json_data --meta-folder ./meta_data
  
  # Принудительно использовать GPU
  python -m index_builder.cli --source-folder ./json_data --device cuda --batch-size 64
  
  # Принудительно использовать CPU
  python -m index_builder.cli --source-folder ./json_data --device cpu
  
  # Выбрать конкретный GPU
  CUDA_VISIBLE_DEVICES=1 python -m index_builder.cli --source-folder ./json_data
        """
    )

    # Основные аргументы
    parser.add_argument('--source-folder', type=str, 
                       default=get_env_path('SOURCE_JSON_FOLDER', './json_data'),
                       help='Folder with JSON content files')
    
    parser.add_argument('--meta-folder', type=str,
                       default=get_env_path('META_JSON_FOLDER', './meta_data'),
                       help='Folder with JSON metadata files')
    
    parser.add_argument('--persist-dir', type=str,
                       default=get_env_path('PERSIST_DIR', './vector_index'),
                       help='Folder where vector DB will be stored')

    # Настройки модели
    parser.add_argument('--model-path', type=str,
                       default=get_env_path('MODEL_PATH', './models/all-MiniLM-L12-v2'),
                       help='Path to local embedding model')
    
    parser.add_argument('--model-name', type=str,
                       help='Remote embedding model name (optional)')

    # Настройки чанкования
    parser.add_argument('--chunk-size', type=int, default=900,
                       help='Chunk size for size-based chunking')
    
    parser.add_argument('--chunk-overlap', type=int, default=150,
                       help='Chunk overlap for size-based chunking')
    
    parser.add_argument('--chunk-by-structure', action='store_true',
                       help='Use structure-based chunking')

    # 🔥 НОВЫЕ ПАРАМЕТРЫ ДЛЯ GPU
    parser.add_argument('--device', type=str, default=None,
                       choices=['cuda', 'cpu', 'auto'],
                       help='Device to use: cuda, cpu, or auto (default: auto)')
    
    parser.add_argument('--batch-size', type=int, default=None,
                       help='Batch size for embedding generation (default: auto-selected based on GPU memory)')
    
    parser.add_argument('--no-gpu', action='store_true',
                       help='Force CPU usage even if GPU is available')
    
    parser.add_argument('--gpu-memory-fraction', type=float, default=None,
                       help='Limit GPU memory usage (e.g., 0.5 for 50%%)')

    # Настройки логирования
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('-v0', '--silent', action='store_true', help='Silent mode')
    log_group.add_argument('-v1', '--short', action='store_true', help='Warnings only')
    log_group.add_argument('-v2', '--normal', action='store_true', help='Normal mode')
    log_group.add_argument('-v3', '--debug', action='store_true', help='Debug mode')
    
    parser.add_argument('--log-dir', type=str,
                       default=get_env_path('LOG_DIR', './logs'),
                       help='Directory for log files')
    
    args = parser.parse_args()

    # Обработка флага --no-gpu
    if args.no_gpu:
        args.device = 'cpu'
        print("💻 Принудительно используем CPU (--no-gpu)")
    
    # Определяем уровень логирования
    verbose_level = 2
    if args.silent:
        verbose_level = 0
    elif args.short:
        verbose_level = 1
    elif args.normal:
        verbose_level = 2
    elif args.debug:
        verbose_level = 3

    # Настройка лимита памяти GPU
    if args.gpu_memory_fraction and torch.cuda.is_available():
        total_memory = torch.cuda.get_device_properties(0).total_memory
        limit = int(total_memory * args.gpu_memory_fraction)
        torch.cuda.set_per_process_memory_fraction(args.gpu_memory_fraction)
        print(f"🎮 Ограничение памяти GPU: {args.gpu_memory_fraction*100:.0f}% ({limit/1024**3:.1f} GB)")

    from .utils.logger import IndexBuilderLogger
    from .core.index_builder import IndexBuilder
    
    log_dir = Path(args.log_dir) if args.log_dir else None
    logger = IndexBuilderLogger.setup_logging(verbose_level, log_dir)
    
    logger.info(f"Environment: {environment}")
    logger.info("🚀 Starting index builder with GPU support")
    logger.info(f"Source folder: {args.source_folder}")
    logger.info(f"Meta folder: {args.meta_folder}")
    logger.info(f"Persist dir: {args.persist_dir}")
    logger.info(f"Chunk by structure: {args.chunk_by_structure}")
    logger.info(f"Device: {args.device or 'auto'}")
    logger.info(f"Batch size: {args.batch_size or 'auto'}")

    # Создаем билдер с GPU поддержкой
    builder = IndexBuilder(
        source_folder=Path(args.source_folder),
        meta_folder=Path(args.meta_folder) if args.meta_folder else None,
        persist_dir=Path(args.persist_dir),
        model_path=args.model_path,
        model_name=args.model_name,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        chunk_by_structure=args.chunk_by_structure,
        device=args.device,
        batch_size=args.batch_size,
        logger=logger
    )
    
    try:
        success = builder.build_index()
        if success:
            logger.info("✅ Index building completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Index building failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during index building: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()