// escenas.js: la puerta de entrada al mundo 3D. El resto de la página habla solo con este archivo
// (lo de adentro está en js/escena/, empezando por mundo.js).
//
// Si el navegador no puede con 3D, nada de eso se carga: la página pasa a "sin-3d" y muestra
// los mismos paneles uno debajo del otro, como una página común.

import { $ } from "./util.js";

/* Las opciones del anillo. El id es el del panel que abren (data-panel en index.html). */
export const OPCIONES = [
  { id: "quien", nombre: "Quién es" },
  { id: "temas", nombre: "Le interesa" },
  { id: "preguntas", nombre: "Se pregunta" },
  { id: "conexiones", nombre: "Conexiones" },
  { id: "cuaderno", nombre: "Cuaderno" },
  { id: "diario", nombre: "Diario" },
  { id: "de-vos", nombre: "De vos" },
  { id: "salud", nombre: "Salud" },
  { id: "charla", nombre: "Charlar", especial: true },
];

let mundo = null;
const ultimo = { tipo: "esperando", temas: [], notas: 0 };
const ganchos = { alElegirTema() {}, alAbrir() {}, puedeCerrar: () => true };

/** ganchos: alElegirTema(nombre), alAbrir(id) y puedeCerrar(id) (la charla no deja cerrar con la sesión activa). */
export async function iniciar(nuevos) {
  Object.assign(ganchos, nuevos);
  try {
    const { crearMundo } = await import("./escena/mundo.js");
    mundo = crearMundo($("#mundo"), {
      opciones: OPCIONES,
      elementoEstado: $("#estado"),
      elementosPanel: [...document.querySelectorAll(".panel")],
      alElegir(accion) {
        if (accion.tipo === "orbe") alternarPanel("ahora");
        else if (accion.tipo === "opcion") alternarPanel(accion.id);
        else if (accion.tipo === "tema") { abrirPanel("temas"); ganchos.alElegirTema(accion.nombre); }
      },
      pedirCerrar: cerrarPanel,
    });
    document.body.classList.add("con-3d");
  } catch (e) {
    console.warn("Sin 3D:", e);
    document.body.classList.add("sin-3d");
    return;
  }
  estado(ultimo.tipo); temas(ultimo.temas); notas(ultimo.notas);
}

/* ---------- paneles ---------- */
export function abrirPanel(id) {
  if (!mundo || mundo.paneles.estaAbierto(id)) { mundo?.paneles.abrir(id); return; }
  mundo.paneles.abrir(id); ganchos.alAbrir(id);
}
export function cerrarPanel(id) { if (ganchos.puedeCerrar(id)) mundo?.paneles.cerrar(id); }
export function alternarPanel(id) { mundo?.paneles.estaAbierto(id) ? cerrarPanel(id) : abrirPanel(id); }
export const panelAbierto = (id) => Boolean(mundo?.paneles.estaAbierto(id));

/* ---------- datos de Angri que el mundo muestra ---------- */
/** Lo que está haciendo: cambia el ritmo del orbe. */
export function estado(tipo) { ultimo.tipo = tipo; mundo?.orbe.estado(tipo); }
/** Los temas que le interesan, [{nombre, peso}]: una luna por cada uno. */
export function temas(lista) { ultimo.temas = lista; mundo?.lunas.poner(lista); }
export function resaltarTema(nombre) { mundo?.lunas.resaltar(nombre); }
/** Cuántas notas tiene: un punto flotando por cada una. */
export function notas(n) { ultimo.notas = n; mundo?.notas.cantidad(n); }
