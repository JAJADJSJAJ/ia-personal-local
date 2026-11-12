#!/bin/sh
# Actualizaciones automáticas de seguridad de Debian para angri. Se corre una vez, como fran (usa sudo).
# - Solo el repositorio de seguridad oficial de Debian: nada de versiones nuevas que cambien cosas.
# - Se instalan a las 05:00, después de que Angri durmió (04:00) y antes de que vuelva a leer.
# - Si alguna necesita reinicio (núcleo), reinicia sola a las 05:30. Al volver, todo arranca solo.
set -e

sudo DEBIAN_FRONTEND=noninteractive apt-get -qq update
sudo DEBIAN_FRONTEND=noninteractive apt-get -qq -y install unattended-upgrades >/dev/null

sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

sudo tee /etc/apt/apt.conf.d/52angri-unattended >/dev/null <<'EOF'
// Angri: solo seguridad (se borra la lista por defecto, que también incluye actualizaciones de versión)
#clear Unattended-Upgrade::Origins-Pattern;
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
};
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";
Unattended-Upgrade::Automatic-Reboot-Time "05:30";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF

# Correr la instalación a las 05:00 (por defecto Debian lo hace a las 06:00 más un azar de hasta una hora)
sudo mkdir -p /etc/systemd/system/apt-daily-upgrade.timer.d
sudo tee /etc/systemd/system/apt-daily-upgrade.timer.d/angri.conf >/dev/null <<'EOF'
[Timer]
OnCalendar=
OnCalendar=*-*-* 05:00
RandomizedDelaySec=10min
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer
echo ACTUALIZACIONES_LISTAS
