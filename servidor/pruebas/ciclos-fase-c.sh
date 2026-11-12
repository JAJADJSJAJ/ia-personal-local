#!/bin/sh
# Corre ciclos forzando el modo, para probar la fase C. Uso: sh ciclos-fase-c.sh [cantidad de ciclos objetivo]
cd /opt/angri/codigo
rm -f ~/pruebas/fasec.log
i=0
while [ $i -lt "${1:-6}" ]; do
  sudo -u angri ANGRI_DATOS=/var/lib/angri ANGRI_MODO=objetivo python3 -m angri.ciclo 2>&1 | tail -3
  i=$((i + 1))
done
echo FIN_CICLOS
