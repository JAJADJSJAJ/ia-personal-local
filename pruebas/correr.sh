#!/bin/sh
# Corre la prueba de calidad contra cada modelo, uno por vez.
# Uso: sh correr.sh [0.8B 2B 4B]
cd "$(dirname "$0")"
mkdir -p resultados
rm -f resultados/listo
for m in ${*:-0.8B 2B 4B}; do
  ~/llama.cpp/build/bin/llama-server -m ~/modelos/Qwen3.5-$m-Q4_K_M.gguf \
    --host 127.0.0.1 --port 8090 -t 4 -c 4096 --jinja > resultados/server-$m.log 2>&1 &
  pid=$!
  until curl -sf http://127.0.0.1:8090/health >/dev/null; do sleep 1; done
  python3 calidad.py "$m" 8090 "resultados/$m.json"
  kill $pid; wait $pid 2>/dev/null
done
echo FIN > resultados/listo
