// rotulos.js: los nombres que acompañan a cada cosa del mundo. Viven en el espacio 3D (se achican
// con la distancia) y siempre miran a la cámara. Dos reglas para que no molesten:
//   - los que quedan del lado de atrás se desvanecen;
//   - si dos se pisarían en pantalla, solo se muestra el que está más adelante.
import { CSS3DSprite, hacia } from "./comun.js";

export function crearRotulos(ctx) {
  const { THREE, vista, camera } = ctx;
  const lista = [], v = new THREE.Vector3();

  function nuevo(elemento, padre, opciones) {
    const sprite = new CSS3DSprite(elemento);
    padre.add(sprite);
    const r = { elemento, sprite, ancho: 0, alto: 0, opacidad: 0, tam: 1, fijo: false, resaltado: false, ...opciones };
    elemento.style.opacity = 0;
    lista.push(r);
    return r;
  }

  return {
    /** Un nombre colgado de un objeto del mundo. Tocarlo vale lo mismo que tocar el objeto. */
    crear(texto, padre, accion, clase = "") {
      const e = document.createElement("div");
      e.className = "rotulo " + clase; e.textContent = texto; e._accion = accion;
      return nuevo(e, padre, {});
    },
    /** Un cartel que no gira con el mundo: queda quieto a la altura que diga alturaY(). */
    fijar(elemento, alturaY) { return nuevo(elemento, ctx.scene, { fijo: true, alturaY }); },
    quitar(r) { r.sprite.removeFromParent(); r.elemento.remove(); lista.splice(lista.indexOf(r), 1); },

    cuadro(t, dt) {
      for (const r of lista) {
        if (r.fijo) r.sprite.position.y = r.alturaY();
        r.sprite.scale.setScalar(vista.px * r.tam);
        r.sprite.getWorldPosition(v);
        r.frente = r.fijo ? 2 : Math.max(0, Math.min(1, (v.z + 2.6) / 5.2));    // 0 = atrás, 1 = adelante
        const lejos = vista.D - v.z;
        v.project(camera);
        if (!r.ancho || r.fijo) { r.ancho = r.elemento.offsetWidth; r.alto = r.elemento.offsetHeight; }
        const e = vista.px * r.tam * vista.foco / lejos;                         // píxeles de pantalla por píxel del cartel
        r.w = r.ancho * e + 8; r.h = r.alto * e + 4;
        r.x = v.x * vista.ancho / 2 - r.w / 2; r.y = -v.y * vista.alto / 2 - r.h / 2;
      }
      const puestos = [];
      for (const r of [...lista].sort((a, b) => (b.fijo - a.fijo) || (b.resaltado - a.resaltado) || (b.frente - a.frente))) {
        let meta = r.fijo || r.resaltado ? 1 : Math.max(0, Math.min(1, (r.frente - .3) / .3));
        const afuera = Math.abs(r.x + r.w / 2) + r.w / 2 > vista.ancho / 2 - 2;          // se saldría por un costado
        if (!r.ancho || afuera || puestos.some((p) => r.x < p.x + p.w && p.x < r.x + r.w && r.y < p.y + p.h && p.y < r.y + r.h)) meta = 0;
        else if (meta > 0) puestos.push(r);
        r.opacidad = hacia(r.opacidad, meta, 10, dt);
        r.elemento.style.opacity = r.opacidad.toFixed(2);
        r.elemento.style.pointerEvents = r.opacidad > .5 && !r.fijo ? "auto" : "none";
      }
    },
  };
}
