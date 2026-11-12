#!/bin/sh
# Baja los dos candidatos de embeddings y corre embeddings.py contra cada uno.
cd "$(dirname "$0")"
M=/opt/angri/modelos
sudo curl -fsSL -C - -o $M/embeddinggemma-300M-Q8_0.gguf \
  https://huggingface.co/ggml-org/embeddinggemma-300M-GGUF/resolve/main/embeddinggemma-300M-Q8_0.gguf
sudo curl -fsSL -C - -o $M/Qwen3-Embedding-0.6B-Q8_0.gguf \
  https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-Q8_0.gguf
sudo chmod a+r $M/*.gguf

probar() {  # archivo, pooling, prefijo consulta, prefijo documento
  echo "=== $1"
  /opt/angri/llama/bin/llama-server -m "$M/$1" --embedding --pooling "$2" --host 127.0.0.1 --port 8091 -t 4 -c 2048 >/tmp/emb.log 2>&1 &
  pid=$!
  until curl -sf http://127.0.0.1:8091/health >/dev/null; do sleep 1; done
  python3 embeddings.py 8091 "$3" "$4"
  kill $pid; wait $pid 2>/dev/null
}
# Prefijos recomendados por cada modelo
probar embeddinggemma-300M-Q8_0.gguf mean "task: search result | query: " "title: none | text: "
probar Qwen3-Embedding-0.6B-Q8_0.gguf last "Instruct: Given a question, retrieve the passage that answers it
Query: " ""
