#!/bin/sh
# Instala o actualiza el código de Angri y su latido. Se corre como fran desde ~/despliegue.
# Espera: ~/despliegue/angri/ (código) y ~/despliegue/sistema/ (servicio, timer, comando).
set -e
D="$HOME/despliegue"

sudo rm -rf /opt/angri/codigo
sudo mkdir -p /opt/angri/codigo
sudo cp -r "$D/angri" /opt/angri/codigo/
sudo find /opt/angri/codigo -name '__pycache__' -prune -exec rm -rf {} +
sudo chown -R root:root /opt/angri/codigo
sudo chmod -R a+rX /opt/angri/codigo

dpkg -s python3-numpy >/dev/null 2>&1 || sudo DEBIAN_FRONTEND=noninteractive apt-get -qq -y install python3-numpy >/dev/null

sudo install -d -o angri -g angri -m 750 /var/lib/angri
sudo install -m 644 "$D/sistema/angri-ciclo.service" "$D/sistema/angri-ciclo.timer" \
  "$D/sistema/llama-emb.service" "$D/sistema/llama-charla.service" "$D/sistema/angri-web.service" /etc/systemd/system/
sudo install -m 755 "$D/sistema/angri" /usr/local/bin/angri
sudo systemctl daemon-reload
sudo systemctl enable --now llama-emb.service llama-charla.service
sudo systemctl restart llama-emb.service llama-charla.service
# El 2B ya no se usa: un solo modelo (4B) para todo
if systemctl is-enabled -q llama-dia.service 2>/dev/null; then sudo systemctl disable --now llama-dia.service; fi
until curl -sf http://127.0.0.1:8082/health >/dev/null; do sleep 2; done
sudo systemctl enable --now angri-ciclo.timer
sudo systemctl enable angri-web.service
sudo systemctl restart angri-web.service
echo INSTALADO
