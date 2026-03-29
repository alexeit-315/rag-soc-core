#!/usr/bin/env python3
"""
Запуск index builder с параллельной обработкой
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from index_builder.core.index_builder import IndexBuilder
from index_builder.utils.logger import IndexBuilderLogger

def main():
    logger = IndexBuilderLogger.setup_logging(2, Path("./logs"))

    builder = IndexBuilder(
        source_folder=Path("../../../../USG6000F/json_data"),
        meta_folder=Path("../../../../USG6000F/meta_data"),
        persist_dir=Path("./vector_index_gpu_optimized"),
        model_path=Path("../../models/all-MiniLM-L12-v2"),
        chunk_by_structure=True,
        device="cuda",
        batch_size=128,
        logger=logger
    )

    # Запуск с параллельной обработкой (4 потока)
    success = builder.build_index_parallel(num_workers=4)

    if success:
        logger.info("✅ Индекс успешно создан!")
    else:
        logger.error("❌ Ошибка создания индекса")

if __name__ == "__main__":
    main()