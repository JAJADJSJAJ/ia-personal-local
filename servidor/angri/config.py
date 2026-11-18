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
USER_AGENT = "AngriBot/0.2 (IA personal local, solo lectura; https://github.com/JAJADJSJAJ/ia-personal-local)"
LARGO_MINIMO = 800      # caracteres: menos que esto no vale la pena
LARGO_MAXIMO = 3000     # se recorta acá (unos 800 tokens)
PAGINAS_POR_DIA = 400   # solo un tope de seguridad por si algo se descontrola: el ritmo lo cuida el contador
WIKI_INTERVALO_SEG = 3        # mínimo entre dos pedidos a Wikipedia
WIKI_PEDIDOS_POR_HORA = 120   # máximo por hora; al llegar, espera a la hora siguiente (sin contar como falla)

# Fase C: temas, novedad y objetivos
TEMA_SIMILITUD = 0.45          # coseno con el centro de un tema para pertenecer a él
TEMA_MINIMO_PARA_NOMBRE = 3    # notas que hacen falta para que un tema exista con nombre
TEMA_OLVIDO_POR_DIA = 0.9      # el peso de un tema se multiplica por esto cada día sin alimentarlo
NOVEDAD_IDEAL = 0.55           # centro de la campana (1 - similitud con lo más parecido que ya sabe)
NOVEDAD_ANCHO = 0.2
PREGUNTA_REPETIDA = 0.85       # coseno con una pregunta anterior: se descarta por repetida
OBJETIVOS_ABIERTOS_MAX = 5
OBJETIVO_PRESUPUESTO = 5       # lecturas por objetivo
OBJETIVO_AGOTADO = 0.9         # si una lectura nueva se parece esto a lo ya anotado, no aportó
PROB_OBJETIVO_BASE = 0.3       # probabilidad de trabajar un objetivo en vez de leer al azar...
PROB_OBJETIVO_MAX = 0.7        # ...que sube con la cantidad de temas, sin pasar de esto
SATURACION = 3                 # ciclos seguidos en el mismo tema antes de forzar un cambio
CANDIDATOS_POR_BUSQUEDA = 3    # artículos que se miran antes de elegir cuál leer
FUENTES_INVESTIGACION = ("es", "en", "wikidata", "it", "fr", "pt", "de")   # orden en que busca
CONSULTAS_FUERA_DEL_ES = 1   # en las otras fuentes se prueba solo la mejor búsqueda, para no gastar pedidos
ARTICULO_SIMILITUD_MINIMA = 0.35  # coseno pregunta ↔ artículo para que valga la pena leerlo
PARRAFOS_POR_LECTURA = 4      # en búsquedas, se leen los párrafos más relacionados con la pregunta

# Fallas (salud.py): no reintentar para siempre ni trabarse en una investigación que rompe
FALLAS_ANTES_DE_ESPERAR = 3    # fallas seguidas antes del primer descanso
ESPERA_INICIAL_MIN = 60        # el descanso se duplica con cada falla nueva...
ESPERA_MAXIMA_MIN = 360        # ...sin pasar de 6 horas
FALLAS_POR_OBJETIVO = 2        # en 24 h: la investigación se abandona como 'fallido'

# Fase D: bandeja de mensajes para Fran
BANDEJA_DIAS = 7               # lo que tiene más de una semana ya no se cuenta
BANDEJA_POR_SALUDO = 3         # novedades que cuenta al abrir la charla

# Charla por navegador (web.py), solo en la red de casa
WEB_PUERTO = int(os.environ.get("ANGRI_WEB_PUERTO", "8080"))

# Fase F: sueño (sueno.py), una vez por noche
DURMIENDO = DATOS / "DURMIENDO"   # mientras existe, el ciclo no corre
SUENO_COPIAS = 7                  # copias de la memoria que se guardan
SUENO_REPETIDA = 0.92             # coseno entre notas de lecturas distintas para juntarlas
                                  # (calibrado: datos distintos del mismo tema dieron hasta 0,77)
SUENO_PREGUNTA_DIAS = 14          # una pregunta que nunca investigó se olvida después de esto
SUENO_PREGUNTAS_MAX = 30          # y si hay más abiertas, se olvidan las más viejas
SUENO_EVENTOS_DIAS = 60
SUENO_LOG_MAXIMO = 50 * 1024 * 1024
SUENO_HECHOS_MAX = 25             # para que el resumen entre en el contexto del modelo

# Fase E: reflexión (reflexion.py), durante el sueño
REFLEXION_NOTAS_MAX = 15        # notas de un tema que se le dan para reflexionar (las más nuevas)
REFLEXION_FRASES_MAX = 8
REFLEXION_PESO_VIVO = 0.5       # debajo de esto, un tema "se le fue enfriando"

# Avisos al celular (avisos.py) por el servidor público ntfy.sh (Fran lo eligió: sale solo el texto del aviso)
AVISOS_ACTIVOS = os.environ.get("ANGRI_AVISOS", "1") == "1"
NTFY_URL = "https://ntfy.sh"
AVISOS_POR_DIA = 2
AVISOS_SEPARACION_HORAS = 3
AVISOS_DESDE_HORA = 10          # nunca de noche ni muy temprano
AVISOS_HASTA_HORA = 22
AVISOS_OPCIONES = 4             # novedades entre las que elige (más "ninguna, hoy no")
AVISOS_ABRIR = "http://angri.local:8080"   # lo que abre tocar el aviso
DUDA_DIAS = 21                  # una duda espera respuesta de Fran (sin insistir) hasta 3 semanas
DUDA_SIMILITUD_CONTEXTO = 0.20  # coseno mensaje ↔ duda si la duda fue lo último que dijo Angri
                                # (calibrado: respuestas reales 0,26-0,45; mensajes sin relación <= 0,16)
DUDA_SIMILITUD = 0.40           # si no estaba en la charla, tiene que parecerse bastante
PROB_DUDA = 0.5               # al dejar una investigación sin respuesta, a veces le pregunta a Fran

# Vigilancia automática (vigilancia.py). Umbrales iniciales: se ajustan con los datos de la primera semana.
VIG_NOTAS_HORAS = 12
VIG_NOTAS_MINIMO = 8            # no se juzga con menos notas que esto
VIG_RECHAZO_MAXIMO = 0.7        # el primer día rechazó ~36%: 70% ya es que algo anda mal
VIG_PAUSA_LECTURA_HORAS = 6
VIG_PREGUNTAS_MINIMO = 6
VIG_REPETIDAS_MAXIMO = 0.5
VIG_TEMAS_MINIMO = 15           # ciclos con tema en la semana para juzgar la concentración
VIG_CUOTA_MAXIMA = 0.6
VIG_PROB_OBJETIVO_BAJA = 0.15   # con el ajuste puesto, la probabilidad de seguir sus preguntas baja a esto
VIG_REFLEXION_NOCHES = 3
VIG_REFLEXION_PARECIDO = 0.97
VIG_BASE_MAXIMA_MB = 10_000     # Fran le da hasta ~100 GB del disco: 10 GB de base + 7 copias de seguridad
VIG_DISCO_MINIMO_GB = 10

# Actividades (actividades.py): lo que puede elegir hacer en cada ciclo
ACT_NOTAS_PARA_EMPEZAR = 5      # recién nacida solo lee al azar hasta tener esto
ACT_REPETICION = 3              # si eligió lo mismo estas veces seguidas, esa sale de la lista un ciclo
ACT_CONECTAR_MIN = 0.35         # dos notas para conectar: ni sin relación...
ACT_CONECTAR_MAX = 0.75         # ...ni casi iguales (calibrado: datos distintos del mismo tema dieron 0,55-0,77)

# Qué está haciendo y charla por la web (ahora.py)
EN_CICLO = DATOS / "EN_CICLO"
CHARLA_WEB = DATOS / "CHARLA_WEB"
CHARLA_WEB_INACTIVIDAD_MIN = 10  # sin mensajes este tiempo, la charla se cierra sola
CHARLA_WEB_LATIDO_SEG = 90       # si la página deja de dar señales (se cerró), se cierra sola

# Verificación de citas
CITA_MINIMA = 25        # caracteres
ANCLAJE_MINIMO = 0.5   # fracción de palabras del resumen que tienen que estar en la fuente
