#!/usr/bin/env python3
"""
Профилирование index builder для выявления узких мест
"""

import cProfile
import pstats
import io
from pathlib import Path
import sys

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from index_builder.core.index_builder import IndexBuilder
from index_builder.utils.logger import IndexBuilderLogger

def run_profiled():
    """Запуск с профилированием"""

    # Настройка логгера
    logger = IndexBuilderLogger.setup_logging(2, None)

    # Создаем билдер
    builder = IndexBuilder(
        source_folder=Path("../../../../USG6000F.old/json_data"),
        meta_folder=Path("../../../../USG6000F.old/meta_data"),
        persist_dir=Path("./vector_index_gpu_profile"),
        model_path=Path("../../models/all-MiniLM-L12-v2"),
        chunk_by_structure=True,
        device="cuda",
        batch_size=128,
        logger=logger
    )

    # Профилируем только загрузку и обработку файлов
    builder.load_embedding_model()

    # Профилируем сбор файлов
    pr = cProfile.Profile()
    pr.enable()

    json_files = builder.collect_json_files()
    print(f"Найдено файлов: {len(json_files)}")

    # Обрабатываем первые 100 файлов для теста
    corpus_chunks = []
    corpus_metas = []

    for i, json_path in enumerate(json_files[:100]):
        if i % 10 == 0:
            print(f"Обработано {i}/100 файлов")
        chunks = builder.process_file(json_path)
        for chunk_text, chunk_meta in chunks:
            corpus_chunks.append(chunk_text)
            corpus_metas.append(chunk_meta)

    pr.disable()

    # Сохраняем результаты
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(30)  # топ-30 функций по времени

    with open('profile_results.txt', 'w', encoding='utf-8') as f:
        f.write(s.getvalue())

    print("\nПрофиль сохранен в profile_results.txt")
    print(f"Всего чанков: {len(corpus_chunks)}")

    # Теперь тестируем GPU на этих чанках
    import torch
    import time

    print("\n" + "="*60)
    print("ТЕСТ GPU НА РЕАЛЬНЫХ ДАННЫХ")
    print("="*60)

    # Очищаем кэш
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    # Замеряем время генерации эмбеддингов
    start_time = time.time()
    embeddings = builder.embed_model.encode(
        corpus_chunks,
        batch_size=128,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
        device="cuda"
    )
    end_time = time.time()

    elapsed = end_time - start_time
    speed = len(corpus_chunks) / elapsed

    print(f"\n📊 Результаты:")
    print(f"   Чанков: {len(corpus_chunks)}")
    print(f"   Время генерации: {elapsed:.2f} сек")
    print(f"   Скорость: {speed:.1f} чанков/сек")
    print(f"   GPU память: {torch.cuda.max_memory_allocated() / 1024**2:.1f} MB")

if __name__ == "__main__":
    run_profiled()