import os, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "ai"))

print("Entrenando Network Transformer...")
subprocess.run([sys.executable, "ai/network_transformer/train.py"], check=True)

print("Entrenando Security Classifier...")
subprocess.run([sys.executable, "ai/security_classifier/train.py"], check=True)

print("Entrenamiento finalizado.")