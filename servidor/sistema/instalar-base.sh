#!/bin/sh
# Prepara el lugar donde vive Angri: usuario propio sin sudo, llama.cpp y modelos en /opt/angri.
# Se corre como fran (con sudo). Se puede repetir sin romper nada.
set -e

# Usuario de sistema, sin contraseña ni sudo
id angri >/dev/null 2>&1 || sudo useradd --system --create-home --home-dir /var/lib/angri --shell /usr/sbin/nologin angri

sudo mkdir -p /opt/angri/modelos

# llama.cpp: solo los programas y librerías que se usan, separados del código fuente de fran
sudo rm -rf /opt/angri/llama
sudo mkdir -p /opt/angri/llama/bin
sudo cp -a "$HOME"/llama.cpp/build/bin/llama-server "$HOME"/llama.cpp/build/bin/llama-cli \
  "$HOME"/llama.cpp/build/bin/llama-bench "$HOME"/llama.cpp/build/bin/llama-cvector-generator \
  "$HOME"/llama.cpp/build/bin/*.so* /opt/angri/llama/bin/
sudo sh -c 'echo /opt/angri/llama/bin > /etc/ld.so.conf.d/angri-llama.conf'
sudo ldconfig

# Modelos de día y de noche
for m in 2B 4B; do
  f="Qwen3.5-$m-Q4_K_M.gguf"
  [ -f "/opt/angri/modelos/$f" ] || sudo cp "$HOME/modelos/$f" /opt/angri/modelos/
done

sudo chown -R root:root /opt/angri
sudo chmod -R a+rX /opt/angri

# Servicio del modelo de día
sudo install -m 644 "$HOME/sistema/llama-dia.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now llama-dia
echo LISTO
