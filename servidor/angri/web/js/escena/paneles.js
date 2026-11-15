// paneles.js: los paneles que saltan al elegir una opción. Son objetos del espacio 3D:
// salen volando desde su opción, flotan delante de todo, se inclinan un poco según dónde están
// y se pueden arrastrar desde la cabecera. En pantallas angostas se muestra uno por vez.
import { CSS3DObject, hacia, estaQuieto } from "./comun.js";

const CERCA = 2.6;          // a qué distancia de la cámara flotan
const MAXIMO = 4;           // cuántos pueden estar abiertos a la vez en pantalla ancha

export function crearPaneles(ctx, { elementos, origen, alCambiar, pedirCerrar }) {
  const { vista, puntero } = ctx;
  const paneles = new Map(), desde = {};
  let turno = 0;

  for (const el of elementos) {
    const objeto = new CSS3DObject(el);
    el.style.userSelect = ""; el.style.opacity = 0;
    ctx.scene.add(objeto);
    const p = { id: el.dataset.panel, el, objeto, abierto: false, k: 0, x: 0, y: 0, ox: 0, oy: 0, vx: 0, ladeo: 0,
      orden: 0, fase: Math.random() * 6, ancho: Number(el.dataset.ancho) || 440, agarre: null };
    paneles.set(p.id, p);

    el.querySelector(".cerrar").addEventListener("click", () => pedirCerrar(p.id));
    el.addEventListener("pointerdown", () => { p.orden = ++turno; });        // tocarlo lo trae adelante

    /* arrastrar desde la cabecera */
    const cabeza = el.querySelector(".panel-cabeza");
    cabeza.addEventListener("pointerdown", (ev) => {
      if (ev.target.closest("button") || ev.button > 0) return;
      p.agarre = { x: ev.clientX, y: ev.clientY };
      cabeza.setPointerCapture(ev.pointerId); el.classList.add("agarrado");
    });
    cabeza.addEventListener("pointermove", (ev) => {
      if (!p.agarre) return;
      const dx = ev.clientX - p.agarre.x, dy = ev.clientY - p.agarre.y;
      p.agarre = { x: ev.clientX, y: ev.clientY };
      p.x += dx; p.y += dy; p.vx = dx;
      limitar(p);
    });
    const soltar = () => { p.agarre = null; el.classList.remove("agarrado"); };
    cabeza.addEventListener("pointerup", soltar);
    cabeza.addEventListener("pointercancel", soltar);
  }

  const anchoDe = (p) => Math.min(p.ancho, vista.ancho - 20);
  /** Que no se pueda llevar un panel fuera de la pantalla: la cabecera siempre queda a mano. */
  function limitar(p) {
    const mx = vista.ancho / 2 - 60, alto = p.el.offsetHeight || 300;
    p.x = Math.max(-mx - anchoDe(p) / 2 + 120, Math.min(mx + anchoDe(p) / 2 - 120, p.x));
    p.y = Math.max(-vista.alto / 2 + alto / 2 + 8, Math.min(vista.alto / 2 + alto / 2 - 56, p.y));
  }
  const abiertos = () => [...paneles.values()].filter((p) => p.abierto);

  /** Elige dónde aparece: en pantalla ancha, a un costado (el que tenga menos paneles); si no, al centro. */
  function ubicar(p) {
    if (vista.angosto) { p.x = 0; p.y = 14; return; }
    const otros = abiertos().filter((o) => o !== p);
    const der = otros.filter((o) => o.x > 0).length, izq = otros.length - der;
    const lado = der <= izq ? 1 : -1, n = lado > 0 ? der : izq;
    p.x = lado * (vista.ancho / 2 - anchoDe(p) / 2 - 28 - n * 34);
    p.y = 18 + n * 40;
  }

  function abrir(id) {
    const p = paneles.get(id);
    if (!p) return;
    p.orden = ++turno;
    if (p.abierto) return;
    if (vista.angosto) abiertos().forEach((o) => cerrar(o.id));
    else if (abiertos().length >= MAXIMO) cerrar(abiertos().sort((a, b) => a.orden - b.orden)[0].id);
    p.el.style.width = anchoDe(p) + "px";
    p.abierto = true; p.objeto.visible = true;
    ubicar(p); salida(p);
    alCambiar(id, true);
  }
  function cerrar(id) {
    const p = paneles.get(id);
    if (!p || !p.abierto) return;
    p.abierto = false; salida(p);
    alCambiar(id, false);
  }
  /** De dónde sale (o adónde vuelve) el panel: el lugar en pantalla de su opción. */
  function salida(p) { ctx.enPantalla(origen(p.id), desde); p.ox = desde.x; p.oy = desde.y; }

  return {
    abrir, cerrar,
    alternar: (id) => (paneles.get(id)?.abierto ? cerrar(id) : abrir(id)),
    estaAbierto: (id) => Boolean(paneles.get(id)?.abierto),
    guardarTodos() { for (const p of paneles.values()) p.objeto.visible = false; },

    alCambiarTamano() {
      const lista = abiertos().sort((a, b) => b.orden - a.orden);
      if (vista.angosto) lista.slice(1).forEach((p) => cerrar(p.id));
      for (const p of lista) { p.el.style.width = anchoDe(p) + "px"; if (vista.angosto) { p.x = 0; p.y = 14; } else limitar(p); }
    },

    cuadro(t, dt) {
      const escala = CERCA / vista.foco;            // a esta distancia, un píxel del panel es un píxel de pantalla
      const quieto = estaQuieto();
      for (const p of paneles.values()) {
        if (!p.objeto.visible) continue;
        p.k = quieto ? Number(p.abierto) : hacia(p.k, p.abierto ? 1 : 0, p.abierto ? 7 : 12, dt);
        if (!p.abierto && p.k < .02) { p.k = 0; p.objeto.visible = false; continue; }
        const k = 1 - Math.pow(1 - p.k, 3);         // sale rápido y frena al llegar
        const flota = quieto || p.agarre ? 0 : Math.sin(t * .7 + p.fase) * 4;
        const x = p.ox + (p.x - p.ox) * k, y = p.oy + (p.y - p.oy) * k + flota * k;
        const z = vista.D - CERCA + p.orden * .0005;
        p.objeto.position.set(x * escala, ctx.camera.position.y - y * escala, z);
        p.objeto.scale.setScalar(escala * (.2 + .8 * k));
        // inclinación: mira un poco hacia el centro, sigue apenas al puntero y se ladea al arrastrarlo
        p.vx *= .85; p.ladeo = hacia(p.ladeo, Math.max(-1, Math.min(1, p.vx / 30)), 10, dt);
        const haciaCentro = vista.angosto ? 0 : -x / vista.ancho * .5;
        p.objeto.rotation.set(quieto ? 0 : puntero.y * .03, haciaCentro + (quieto ? 0 : puntero.x * .035) + p.ladeo * .22 + (1 - k) * .6, p.ladeo * -.05);
        p.el.style.opacity = Math.min(1, p.k * 1.6).toFixed(2);
      }
    },
  };
}
