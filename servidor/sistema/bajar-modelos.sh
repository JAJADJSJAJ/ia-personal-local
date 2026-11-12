#!/bin/sh
# Baja los modelos candidatos de Qwen3.5 en Q4_K_M a ~/modelos.
# Uso: sh bajar-modelos.sh [0.8B 2B 4B]
set -e
mkdir -p "$HOME/modelos"
cd "$HOME/modelos"
rm -f bajada.ok
for m in ${*:-0.8B 2B 4B}; do
  f="Qwen3.5-$m-Q4_K_M.gguf"
  echo "Bajando $f"
  curl -fSL --retry 5 -C - -o "$f" "https://huggingface.co/unsloth/Qwen3.5-$m-GGUF/resolve/main/$f"
done
ls -la
echo FIN > bajada.ok
