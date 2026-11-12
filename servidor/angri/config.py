"""Configuración de Angri. Todo lo ajustable vive acá."""
import os
from pathlib import Path

# Dónde guarda todo lo suyo (en angri: /var/lib/angri). Se puede cambiar para probar.
DATOS = Path(os.environ.get("ANGRI_DATOS", "/var/lib/angri"))
BASE = DATOS / "memoria.db"
DIARIO = DATOS / "diario"
LOGS = DATOS / "logs"
PAUSA = DATOS / "PAUSA"  # si existe este archivo, no hace nada

# Un solo modelo para todo: Qwen3.5 4B (servicio llama-charla). El 2B inventaba escenas
# al conversar y el 0.8B no copiaba citas (pruebas/RESULTADOS-calidad.md).
MODELO_URL = os.environ.get("ANGRI_MODELO", "http://127.0.0.1:8082/v1/chat/completions")
CHARLA_URL = os.environ.get("ANGRI_CHARLA", MODELO_URL)
MUESTREO = {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "presence_penalty": 1.5}
MAX_TOKENS = 400
TIMEOUT_MODELO = 600

# Embeddings (servicio llama-emb). Los prefijos dependen del modelo elegido.
EMB_URL = os.environ.get("ANGRI_EMB", "http://127.0.0.1:8081/v1/embeddings")
EMB_PREFIJO_CONSULTA = "task: search result | query: "
EMB_PREFIJO_DOC = "title: none | text: "

# Recuperación (Generative Agents): recencia + importancia + relevancia
RECENCIA_POR_HORA = 0.995
RECUERDOS_POR_TURNO = 4
# Coseno absoluto mínimo. Calibrado con embeddinggemma (pruebas/calibrar-similitud.py):
# lo relacionado dio >= 0,39 y lo que no tiene que ver <= 0,26.
SIMILITUD_MINIMA = float(os.environ.get("ANGRI_SIMILITUD_MINIMA", "0.32"))
RELEVANCIA_MINIMA = 0.6  # relativa al mejor candidato: un modelo chico se pierde con recuerdos de relleno
PRESUPUESTO_RECUERDOS = 3200   # caracteres (unos 800 tokens)

# Charla
CHARLANDO = DATOS / "CHARLANDO"   # mientras existe y es reciente, el ciclo de fondo no corre
CHARLA_PAUSA_MINUTOS = 10
TURNOS_DE_CONTEXTO = 6

# Lectura
USER_AGENT = "AngriBot/0.1 (IA personal local, solo lectura)"
LARGO_MINIMO = 800      # caracteres: menos que esto no vale la pena
LARGO_MAXIMO = 3000     # se recorta acá (unos 800 tokens)
PAGINAS_POR_DIA = 60    # presupuesto

# Verificación de citas
CITA_MINIMA = 25        # caracteres
ANCLAJE_MINIMO = 0.5   # fracción de palabras del resumen que tienen que estar en la fuente
