"""Configuración de Angri. Todo lo ajustable vive acá."""
import os
from pathlib import Path

# Dónde guarda todo lo suyo (en angri: /var/lib/angri). Se puede cambiar para probar.
DATOS = Path(os.environ.get("ANGRI_DATOS", "/var/lib/angri"))
BASE = DATOS / "memoria.db"
DIARIO = DATOS / "diario"
LOGS = DATOS / "logs"
PAUSA = DATOS / "PAUSA"  # si existe este archivo, no hace nada

# Modelo de día (servicio llama-dia)
MODELO_URL = os.environ.get("ANGRI_MODELO", "http://127.0.0.1:8080/v1/chat/completions")
MUESTREO = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "presence_penalty": 1.5}
MAX_TOKENS = 400
TIMEOUT_MODELO = 300

# Lectura
USER_AGENT = "AngriBot/0.1 (IA personal local, solo lectura)"
LARGO_MINIMO = 800      # caracteres: menos que esto no vale la pena
LARGO_MAXIMO = 3000     # se recorta acá (unos 800 tokens)
PAGINAS_POR_DIA = 60    # presupuesto

# Verificación de citas
CITA_MINIMA = 25        # caracteres
ANCLAJE_MINIMO = 0.5   # fracción de palabras del resumen que tienen que estar en la fuente
