"""Embeddings: convierte textos en vectores para buscar por significado (servicio llama-emb)."""
import json
import urllib.request

import numpy as np

from . import config


def _pedir(textos: list[str]) -> np.ndarray:
    pedido = urllib.request.Request(
        config.EMB_URL, data=json.dumps({"input": textos}).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(pedido, timeout=120) as r:
        datos = json.load(r)["data"]
    m = np.array([d["embedding"] for d in sorted(datos, key=lambda d: d["index"])], dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)  # normalizados: el producto punto es el coseno


def documentos(textos: list[str]) -> np.ndarray:
    return _pedir([config.EMB_PREFIJO_DOC + t for t in textos])


def consulta(texto: str) -> np.ndarray:
    return _pedir([config.EMB_PREFIJO_CONSULTA + texto])[0]
