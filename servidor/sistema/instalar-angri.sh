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

sudo install -d -o angri -g angri -m 750 /var/lib/angri
sudo install -m 644 "$D/sistema/angri-ciclo.service" "$D/sistema/angri-ciclo.timer" /etc/systemd/system/
sudo install -m 755 "$D/sistema/angri" /usr/local/bin/angri
sudo systemctl daemon-reload
sudo systemctl enable --now angri-ciclo.timer
echo INSTALADO
