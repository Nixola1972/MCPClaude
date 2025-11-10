#!/usr/bin/env python3
"""
Script per verificare se Ollama sta usando GPU o CPU
"""

import subprocess
import requests
import json
import time
import threading

print("=" * 80)
print("VERIFICA USO GPU DA OLLAMA")
print("=" * 80)

# ===== TEST 1: CUDA DISPONIBILE SUL SISTEMA =====
print("\n" + "=" * 80)
print("TEST 1: CUDA DISPONIBILE SUL SISTEMA")
print("=" * 80)

try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("✅ nvidia-smi funziona, CUDA è disponibile\n")

        # Parse GPU info
        lines = result.stdout.split('\n')
        for line in lines:
            if 'RTX' in line or 'GTX' in line or 'Tesla' in line:
                print(f"   🎮 GPU trovata: {line.strip()}")

        # Show VRAM
        print("\n   💾 VRAM disponibile:")
        for line in lines:
            if 'MiB' in line and '/' in line:
                print(f"      {line.strip()}")
    else:
        print("❌ nvidia-smi non funziona, CUDA non disponibile")
except FileNotFoundError:
    print("❌ nvidia-smi non trovato, driver NVIDIA non installati")
except Exception as e:
    print(f"❌ Errore: {e}")

# ===== TEST 2: OLLAMA È ATTIVO =====
print("\n" + "=" * 80)
print("TEST 2: OLLAMA ATTIVO")
print("=" * 80)

try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("✅ Ollama è ATTIVO")
        models = response.json().get('models', [])
        print(f"   Modelli disponibili: {len(models)}")

        # Check for gemma3:12b
        has_gemma = any('gemma3:12b' in m['name'] for m in models)
        if has_gemma:
            print("   ✅ gemma3:12b disponibile")
        else:
            print("   ⚠️  gemma3:12b NON trovato")
    else:
        print(f"❌ Ollama risponde con errore: {response.status_code}")
        exit(1)
except requests.exceptions.ConnectionError:
    print("❌ Ollama NON è attivo!")
    print("   Avvialo con: ollama serve")
    exit(1)
except Exception as e:
    print(f"❌ Errore: {e}")
    exit(1)

# ===== TEST 3: VERIFICA UTILIZZO GPU DURANTE GENERAZIONE =====
print("\n" + "=" * 80)
print("TEST 3: VERIFICA USO GPU DURANTE GENERAZIONE")
print("=" * 80)
print("\n📊 Stato GPU PRIMA della generazione:")

try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print(result.stdout)
except:
    pass

print("=" * 80)
print("⏳ Invio richiesta a Ollama (test generazione)...")
print("   Modello: gemma3:12b")
print("   Prompt: breve test in italiano")
print("=" * 80)

# Monitor GPU usage during generation
gpu_stats = []
monitoring = True

def monitor_gpu():
    """Monitor GPU usage in background"""
    while monitoring:
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for idx, line in enumerate(lines):
                    parts = line.split(',')
                    if len(parts) == 2:
                        mem_used = int(parts[0].strip())
                        gpu_util = int(parts[1].strip())
                        gpu_stats.append({'gpu': idx, 'mem': mem_used, 'util': gpu_util})
        except:
            pass
        time.sleep(0.5)

# Start monitoring thread
monitor_thread = threading.Thread(target=monitor_gpu, daemon=True)
monitor_thread.start()

# Send request to Ollama
start_time = time.time()

try:
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "gemma3:12b",
        "prompt": "Rispondi in italiano: cos'è l'intelligenza artificiale? (massimo 50 parole)",
        "stream": False,
        "options": {"temperature": 0.3}
    }, timeout=120)

    elapsed = time.time() - start_time
    monitoring = False
    time.sleep(0.5)  # Wait for last stats

    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Risposta ricevuta in {elapsed:.1f} secondi")
        print(f"\n📝 Risposta: {result['response'][:200]}...\n")
    else:
        print(f"\n❌ Errore: {response.status_code}")
        monitoring = False
        exit(1)

except Exception as e:
    print(f"\n❌ Errore durante generazione: {e}")
    monitoring = False
    exit(1)

# ===== ANALISI USO GPU =====
print("=" * 80)
print("ANALISI USO GPU DURANTE GENERAZIONE")
print("=" * 80)

if len(gpu_stats) > 0:
    # Group by GPU
    gpu_data = {}
    for stat in gpu_stats:
        gpu_id = stat['gpu']
        if gpu_id not in gpu_data:
            gpu_data[gpu_id] = {'mem': [], 'util': []}
        gpu_data[gpu_id]['mem'].append(stat['mem'])
        gpu_data[gpu_id]['util'].append(stat['util'])

    for gpu_id, data in gpu_data.items():
        max_mem = max(data['mem'])
        avg_mem = sum(data['mem']) / len(data['mem'])
        max_util = max(data['util'])
        avg_util = sum(data['util']) / len(data['util'])

        print(f"\n🎮 GPU {gpu_id}:")
        print(f"   💾 VRAM usata: {avg_mem:.0f} MB (media), {max_mem} MB (max)")
        print(f"   ⚡ Utilizzo GPU: {avg_util:.0f}% (media), {max_util}% (max)")

        # Determine if GPU is being used
        if max_util > 10 or max_mem > 1000:
            print(f"   ✅ GPU ATTIVAMENTE USATA!")
        else:
            print(f"   ⚠️  GPU NON usata o uso minimo")
else:
    print("⚠️  Non sono riuscito a monitorare l'uso GPU")

print("\n" + "=" * 80)
print("📊 Stato GPU DOPO la generazione:")

try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print(result.stdout)
except:
    pass

# ===== CONCLUSIONI =====
print("=" * 80)
print("CONCLUSIONI")
print("=" * 80)

if len(gpu_stats) > 0:
    max_mem_overall = max([max(data['mem']) for data in gpu_data.values()])
    max_util_overall = max([max(data['util']) for data in gpu_data.values()])

    if max_util_overall > 20 and max_mem_overall > 2000:
        print("\n✅ OLLAMA STA USANDO LA GPU CORRETTAMENTE!")
        print(f"   Utilizzo GPU max: {max_util_overall}%")
        print(f"   VRAM usata max: {max_mem_overall} MB")
    elif max_mem_overall > 1000 and max_util_overall < 10:
        print("\n⚠️  OLLAMA USA GPU PER MEMORIA MA NON PER COMPUTE")
        print("   Possibile causa: modello caricato in VRAM ma inferenza su CPU")
        print(f"   VRAM usata: {max_mem_overall} MB")
        print(f"   GPU compute: {max_util_overall}%")
    else:
        print("\n❌ OLLAMA STA USANDO LA CPU, NON LA GPU!")
        print(f"   GPU utilization: {max_util_overall}% (troppo basso)")
        print(f"   VRAM usata: {max_mem_overall} MB")
        print("\n🔧 POSSIBILI SOLUZIONI:")
        print("   1. Verifica driver NVIDIA aggiornati")
        print("   2. Reinstalla Ollama con supporto CUDA:")
        print("      curl -fsSL https://ollama.com/install.sh | sh")
        print("   3. Verifica variabili ambiente:")
        print("      echo $CUDA_VISIBLE_DEVICES")
        print("   4. Forza GPU con:")
        print("      CUDA_VISIBLE_DEVICES=0 ollama serve")
        print("   5. Verifica che Ollama sia compilato con CUDA:")
        print("      ollama --version")
else:
    print("\n⚠️  Impossibile determinare uso GPU")

print("=" * 80)
