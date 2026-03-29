#!/usr/bin/env python3
"""
Мониторинг GPU в реальном времени
"""

import subprocess
import time
import sys
from datetime import datetime

def get_gpu_stats():
    """Получает статистику GPU через nvidia-smi"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, encoding='utf-8'
        )
        return result.stdout.strip()
    except:
        return None

def monitor_gpu(interval=1):
    """Мониторинг GPU с заданным интервалом"""
    print("="*60)
    print("МОНИТОРИНГ GPU")
    print("="*60)
    print(f"{'Время':<20} {'GPU Util':<10} {'Memory':<15} {'Temp':<10}")
    print("-"*60)
    
    try:
        while True:
            stats = get_gpu_stats()
            if stats:
                now = datetime.now().strftime("%H:%M:%S")
                # Ожидаем формат: "13, 1701, 4096, 32"
                parts = stats.split(',')
                if len(parts) >= 4:
                    gpu_util = parts[0].strip()
                    mem_used = parts[1].strip()
                    mem_total = parts[2].strip()
                    temp = parts[3].strip()
                    
                    print(f"{now:<20} {gpu_util:>3}% {' ':>2} {mem_used:>4}/{mem_total:<4} MB {temp:>3}°C")
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n" + "-"*60)
        print("Мониторинг остановлен")

if __name__ == "__main__":
    interval = 1
    if len(sys.argv) > 1:
        interval = float(sys.argv[1])
    monitor_gpu(interval)