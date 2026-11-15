// mundo.js: el espacio 3D entero. Arma la cámara, las luces y el reloj, y escucha el puntero.
//
// Qué hay adentro (cada cosa en su archivo):
//   orbe.js     Angri, en el centro. Tocarla abre "Ahora".
//   menu.js     las opciones, girando en un anillo debajo de ella. Tocar una abre su panel.
//   lunas.js    sus temas, en órbita alrededor. Tocar uno abre "Le interesa" en ese tema.
//   notas.js    un punto flotando por cada nota de su cuaderno.
//   rotulos.js  los nombres que acompañan a cada cosa (no se pisan entre sí).
//   paneles.js  los paneles que saltan al elegir una opción: vuelan, se arrastran y se cierran.
//
// Arrastrar el vacío gira todo; la rueda acerca o aleja.

import { THREE, CSS3DRenderer, hacia, estaQuieto } from "./comun.js";
import { crearOrbe } from "./orbe.js";
import { crearMenu } from "./menu.js";
import { crearLunas } from "./lunas.js";
import { crearNotas } from "./notas.js";
import { crearRotulos } from "./rotulos.js";
import { crearPaneles } from "./paneles.js";

const FOV = 40, TAN = Math.tan(FOV * Math.PI / 360), BAJA = -.42;

/**
 * raiz: el <div> que ocupa toda la pantalla.
 * opciones: [{id, nombre, especial}] para el anillo.   elementoEstado: el cartel de arriba.
 * alElegir(accion): avisa qué se tocó ({tipo: "opcion"|"tema"|"orbe", ...}).
 */
export function crearMundo(raiz, { opciones, elementoEstado, elementosPanel, alElegir, pedirCerrar }) {
  const canvas = document.createElement("canvas");
  const gl = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });   // tira error si no hay WebGL
  gl.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  const css = new CSS3DRenderer();
  css.domElement.classList.add("capa-3d");
  // Que el navegador no corra la capa de lado al enfocar algo de un panel (pasa aunque no tenga barra de desplazamiento).
  css.domElement.style.overflow = "clip";
  raiz.addEventListener("scroll", (ev) => { if (!ev.target.closest?.(".panel")) ev.target.scrollLeft = ev.target.scrollTop = 0; }, true);
  raiz.append(canvas, css.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV, 1, .1, 80);
  const inclinado = new THREE.Group(), giratorio = new THREE.Group();   // arrastrar: arriba/abajo inclina, a los lados gira
  inclinado.add(giratorio);
  const sol = new THREE.DirectionalLight(0xffffff, 1.6); sol.position.set(-3, 4, 5);
  scene.add(inclinado, new THREE.HemisphereLight(0xffffff, 0x8fa3ad, 1.7), sol);

  // Las medidas que todas las piezas consultan. Se recalculan al cambiar el tamaño de la ventana.
  const vista = { ancho: 1, alto: 1, angosto: false, R: 2.5, D: 9, foco: 1, px: 1, t: 0 };
  const puntero = { x: 0, y: 0, dentro: false };        // de -1 a 1, para el paralaje y para saber qué se señala
  const ctx = { THREE, scene, giratorio, camera, vista, puntero, sobre: null, alElegir,
    /** Dónde cae en la pantalla un objeto del mundo, en píxeles desde el centro. */
    enPantalla(objeto, destino = {}) {
      objeto.getWorldPosition(v).project(camera);
      destino.x = v.x * vista.ancho / 2; destino.y = -v.y * vista.alto / 2;
      return destino;
    },
    blancos: [],                                          // lo que se puede tocar
  };
  const v = new THREE.Vector3();

  const orbe = crearOrbe(ctx);
  const rotulos = crearRotulos(ctx);
  ctx.rotulos = rotulos;
  const menu = crearMenu(ctx, opciones);
  const lunas = crearLunas(ctx);
  const notas = crearNotas(ctx);
  const paneles = crearPaneles(ctx, { elementos: elementosPanel, pedirCerrar, origen: (id) => menu.objeto(id) || orbe.malla,
    alCambiar: (id, abierto) => menu.marcar(id, abierto) });
  rotulos.fijar(elementoEstado, () => BAJA + Math.min(TAN * vista.D - 70 * vista.px, 3.5));    // el cartel de estado, arriba de todo
  const piezas = [orbe, menu, lunas, notas, rotulos, paneles];

  /* ---------- tamaño ---------- */
  let zoom = 1, zoomMeta = 1, inclina = .27, inclinaMeta = .27, tocoInclinar = false;
  function medir() {
    const ancho = raiz.clientWidth, alto = raiz.clientHeight;
    if (ancho < 2 || alto < 2) return;
    const forma = ancho / alto;
    Object.assign(vista, { ancho, alto, angosto: forma < .8, R: forma < .8 ? 2.0 : 2.5, foco: alto / 2 / TAN });
    vista.Dbase = Math.max(3.5 / TAN, (vista.R + 1.1) / (TAN * forma));   // que entre todo, a lo alto y a lo ancho
    gl.setSize(ancho, alto, false); css.setSize(ancho, alto);
    camera.aspect = forma; camera.updateProjectionMatrix();
    if (!tocoInclinar) inclinaMeta = vista.angosto ? .42 : .27;       // en pantallas altas se mira un poco más de arriba
    alejar();
    for (const p of piezas) p.alCambiarTamano?.();
  }
  function alejar() {
    vista.D = vista.Dbase * zoom; vista.px = vista.D / vista.foco;   // px: cuánto mide un píxel a la altura del orbe
    camera.position.set(0, BAJA, vista.D);                             // un poco baja: deja lugar al anillo de opciones
  }
  new ResizeObserver(medir).observe(raiz);
  medir();

  /* ---------- puntero: girar, señalar y tocar ---------- */
  let giro = .5, giroVel = 0, arrastre = null, quietoDesde = 0;
  const rayo = new THREE.Raycaster(), ndc = new THREE.Vector2();
  function queHay(ev) {
    const r = raiz.getBoundingClientRect();
    ndc.set((ev.clientX - r.left) / r.width * 2 - 1, -(ev.clientY - r.top) / r.height * 2 + 1);
    rayo.setFromCamera(ndc, camera);
    for (let o = rayo.intersectObjects(ctx.blancos, false)[0]?.object; o; o = o.parent) if (o.userData.accion) return o.userData.accion;
    return null;
  }
  raiz.addEventListener("pointerdown", (ev) => {
    if (ev.target.closest(".panel") || ev.button > 0) return;
    arrastre = { x: ev.clientX, y: ev.clientY, camino: 0, rotulo: ev.target.closest(".rotulo") };
    raiz.setPointerCapture(ev.pointerId); giroVel = 0;
  });
  raiz.addEventListener("pointermove", (ev) => {
    const r = raiz.getBoundingClientRect();
    puntero.x = (ev.clientX - r.left) / r.width * 2 - 1; puntero.y = (ev.clientY - r.top) / r.height * 2 - 1;
    if (arrastre) {
      const dx = ev.clientX - arrastre.x, dy = ev.clientY - arrastre.y;
      arrastre.x = ev.clientX; arrastre.y = ev.clientY; arrastre.camino += Math.abs(dx) + Math.abs(dy);
      if (arrastre.camino > 6) {
        raiz.classList.add("girando"); raiz.classList.remove("sin-tocar");
        giroVel = dx * .006; giro += giroVel;
        tocoInclinar = true;
        inclinaMeta = Math.max(.02, Math.min(.85, inclinaMeta + dy * .004));
      }
    } else if (ev.pointerType === "mouse") {
      ctx.sobre = ev.target.closest(".panel") ? null : (ev.target.closest(".rotulo")?._accion || queHay(ev));
      raiz.classList.toggle("senalando", Boolean(ctx.sobre));
    }
  });
  const soltar = (ev) => {
    if (!arrastre) return;
    const toque = arrastre.camino <= 6, rotulo = arrastre.rotulo;
    arrastre = null; raiz.classList.remove("girando"); quietoDesde = vista.t;
    if (toque && ev.type === "pointerup") {
      const accion = rotulo?._accion || queHay(ev);
      if (accion) { raiz.classList.remove("sin-tocar"); alElegir(accion); }
    }
  };
  raiz.addEventListener("pointerup", soltar);
  raiz.addEventListener("pointercancel", soltar);
  raiz.addEventListener("pointerleave", () => { ctx.sobre = null; raiz.classList.remove("senalando"); });
  raiz.addEventListener("wheel", (ev) => {
    if (ev.target.closest(".panel")) return;              // adentro de un panel, la rueda desplaza su texto
    ev.preventDefault();
    zoomMeta = Math.max(.72, Math.min(1.45, zoomMeta * Math.exp(ev.deltaY * .0011)));
  }, { passive: false });

  /* ---------- el reloj: un cuadro por vez, y nada con la pestaña oculta ---------- */
  let antes = performance.now();
  function vuelta(ahora) {
    requestAnimationFrame(vuelta);
    const dt = Math.min(.05, (ahora - antes) / 1000); antes = ahora;
    if (document.hidden || vista.ancho < 2) return;
    vista.t += dt;
    if (Math.abs(zoom - zoomMeta) > .0005) { zoom = hacia(zoom, zoomMeta, 7, dt); alejar(); }
    if (!arrastre) {
      giro += giroVel; giroVel *= .93;
      // sola, gira muy despacio; se frena al señalar algo y con "reducir movimiento"
      if (!estaQuieto() && !ctx.sobre && vista.t - quietoDesde > 1.5) giro += dt * .045;
    }
    inclina = hacia(inclina, inclinaMeta, 9, dt);
    giratorio.rotation.y = giro;
    inclinado.rotation.x = inclina + (estaQuieto() ? 0 : puntero.y * .025);
    scene.updateMatrixWorld();
    for (const p of piezas) p.cuadro?.(vista.t, dt);
    gl.render(scene, camera);
    css.render(scene, camera);
  }
  css.render(scene, camera);          // primer dibujo con todo visible: así cada panel queda colgado en la página
  paneles.guardarTodos();
  requestAnimationFrame(vuelta);

  return { orbe, lunas, notas, paneles, menu };
}
