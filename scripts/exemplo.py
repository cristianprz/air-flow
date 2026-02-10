"""
Script de exemplo para testar o AirFlow Lite.
"""
import time
import random
from datetime import datetime

print(f"[{datetime.now()}] Iniciando script de exemplo...")
print(f"Python script runner funcionando!")
print()

for i in range(1, 6):
    print(f"  Passo {i}/5 - Processando...")
    time.sleep(1)

resultado = random.choice(["sucesso", "concluído", "finalizado"])
print()
print(f"[{datetime.now()}] Script {resultado} com êxito!")
print(f"Tempo total: ~5 segundos")
