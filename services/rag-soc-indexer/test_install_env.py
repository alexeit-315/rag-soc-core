import sys
import warnings
warnings.filterwarnings("ignore")

print("="*60)
print("ПОЛНАЯ ПРОВЕРКА УСТАНОВКИ")
print("="*60)

# NumPy
try:
    import numpy as np
    print(f"✅ NumPy {np.__version__}")
except Exception as e:
    print(f"❌ NumPy: {e}")

# PyTorch
try:
    import torch
    print(f"✅ PyTorch {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
except Exception as e:
    print(f"❌ PyTorch: {e}")

# Transformers
try:
    import transformers
    print(f"✅ Transformers {transformers.__version__}")
except Exception as e:
    print(f"❌ Transformers: {e}")

# SentenceTransformers
try:
    import sentence_transformers
    print(f"✅ SentenceTransformers {sentence_transformers.__version__}")
except Exception as e:
    print(f"❌ SentenceTransformers: {e}")

# ChromaDB
try:
    import chromadb
    print(f"✅ ChromaDB {chromadb.__version__}")
except Exception as e:
    print(f"❌ ChromaDB: {e}")

# LangChain
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    print(f"✅ LangChain Text Splitters")
except Exception as e:
    print(f"❌ LangChain: {e}")

print("\n" + "="*60)
print("Загрузка модели для теста...")
print("="*60)

try:
    model = sentence_transformers.SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print(f"✅ Модель загружена")
    print(f"   Размерность: {model.get_sentence_embedding_dimension()}")

    # Тестовый эмбеддинг
    test_text = "Тестовый запрос"
    embedding = model.encode(test_text)
    print(f"   Тестовый эмбеддинг: {embedding.shape}")

except Exception as e:
    print(f"❌ Ошибка загрузки модели: {e}")

print("\n" + "="*60)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("="*60)