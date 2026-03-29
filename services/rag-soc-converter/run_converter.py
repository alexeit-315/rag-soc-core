# run_converter.py
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from hdx_converter.cli import main

if __name__ == "__main__":
    main()