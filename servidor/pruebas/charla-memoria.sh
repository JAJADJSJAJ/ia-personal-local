#!/bin/sh
# Prueba de la fase B: ¿usa los recuerdos para responder? Usa el modelo instalado (4B).
# Empieza de cero: borra episodios, le cuenta un dato en una charla y le pregunta en otra.
cd /opt/angri/codigo
sudo -u angri ANGRI_DATOS=/var/lib/angri python3 ~/pruebas/limpiar-episodios.py
printf 'Te cuento algo: mi perro se llama Toto y es re comilón.\nchau\n' |
  sudo -u angri ANGRI_DATOS=/var/lib/angri python3 -m angri.charla >/dev/null
printf 'Che, ¿te acordás cómo se llama mi perro?\n¿Leíste algo sobre volcanes últimamente?\n¿Y sabés cuál es mi color favorito?\nchau\n' |
  sudo -u angri ANGRI_DATOS=/var/lib/angri python3 -m angri.charla --recuerdos
