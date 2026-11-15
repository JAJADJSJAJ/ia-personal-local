// charla.js: el panel de la charla. Se inicia a propósito, se termina con un botón,
// y se cierra sola si pasan 10 minutos sin mensajes o si se cierra la página.
import { $, el, mmss } from "./util.js";
import { api, clave } from "./api.js";
import { cargar } from "./panel.js";
import * as escenas from "./escenas.js";

const MIN_CHARLA = 10 * 60;
const LARGO = 2 * Math.PI * 13;   // el contorno del relojito
let sesion = null, ocupado = false, finCharla = 0, latidoId = null, relojId = null;

/* ---------- abrir y cerrar el panel ---------- */
/** Con la charla activa el panel no se puede cerrar: primero hay que terminarla. */
export const puedeCerrar = (id) => id !== "charla" || !sesion;
/** Al abrirse se anota en el historial, así el botón "atrás" del celular la cierra. */
export function alAbrir(id) { if (id === "charla") history.pushState({ charla: true }, ""); }

/* ---------- mensajes ---------- */
function burbuja(quien, texto) {
  const m = el("div", "mensaje " + quien);
  if (quien === "angri") m.append(el("div", "orbe-mini"));
  const b = el("div", "burbuja"); if (texto != null) b.textContent = texto; m.append(b);
  $("#mensajes").append(m);
  const cuerpo = $("#charla-cuerpo"); cuerpo.scrollTop = cuerpo.scrollHeight;
  return b;
}
function escribiendo() {
  const b = burbuja("angri"); b.classList.add("escribiendo"); b.append(el("span"), el("span"), el("span"));
  return b.parentElement;
}

/* ---------- reloj de inactividad ---------- */
function pintarReloj() {
  const s = Math.max(0, Math.round((finCharla - Date.now()) / 1000));
  $("#reloj-txt").textContent = mmss(s);
  $("#reloj-arco").style.strokeDashoffset = LARGO * (1 - s / MIN_CHARLA);
  $("#reloj").classList.toggle("poco", s < 90);
  if (s === 0 && sesion) charlaCerrada("Pasaron 10 minutos sin mensajes: la charla se cerró sola y Angri siguió con lo suyo.");
}
function ponerReloj(seg) { finCharla = Date.now() + seg * 1000; pintarReloj(); }

function modoCharla(activa) {
  $("#volver").disabled = activa;
  $("#charla-pie").hidden = !activa; $("#reloj").hidden = !activa;
  $("#charla-sub").textContent = activa ? "Angri dejó lo que hacía y te está escuchando" : "Todavía no empezó";
  clearInterval(latidoId); clearInterval(relojId);
  if (activa) {
    latidoId = setInterval(async () => {
      try { const d = await api("/api/charla/latido", { sesion }); ponerReloj(d.restante); }
      catch (e) { if (e.status === 409) charlaCerrada("La charla se cerró."); }
    }, 30000);
    relojId = setInterval(pintarReloj, 1000);
  }
}

/* ---------- iniciar, hablar, terminar ---------- */
const DEJO = { azar: "lo que estaba leyendo", objetivo: "lo que estaba investigando", repasar: "sus repasos",
  conectar: "lo que estaba conectando", pensar: "lo que estaba pensando", descansar: "su descanso", dormir: "su sueño" };

async function iniciar() {
  const b = $("#iniciar"); b.disabled = true; b.textContent = "Avisándole…";
  try {
    const d = await api("/api/charla/iniciar", { sesion });
    sesion = d.sesion;
    $("#inicio-charla").remove();
    burbuja("sistema", d.cortado ? `Angri dejó ${DEJO[d.cortado] || "lo que hacía"} para charlar con vos.` : "Charla iniciada.");
    modoCharla(true); ponerReloj(d.restante);
    if (d.texto) burbuja("angri", d.texto);
    $("#texto").focus();
  } catch (e) {
    b.disabled = false; b.textContent = "Iniciar charla";
    if (e.message !== "clave") burbuja("sistema", "No pude iniciar la charla: " + e.message);
  }
}

async function enviar(ruta, cuerpo, mostrar) {
  if (ocupado || !sesion) return;
  ocupado = true; $("#enviar").disabled = true;
  if (mostrar) burbuja("vos", mostrar);
  const espera = escribiendo();
  try {
    const d = await api(ruta, { ...cuerpo, sesion });
    espera.remove(); burbuja("angri", d.texto); ponerReloj(d.restante);
  } catch (e) {
    espera.remove();
    if (e.status === 409) charlaCerrada(e.message); else if (e.message !== "clave") burbuja("sistema", e.message);
  } finally {
    ocupado = false; $("#enviar").disabled = false;
  }
}

async function terminar() {
  if (!sesion) return;
  const s = sesion; sesion = null;
  try { await api("/api/charla/terminar", { sesion: s }); } catch (e) {}
  charlaCerrada("Charla terminada. Angri sigue con lo suyo.");
}

function charlaCerrada(texto) {
  sesion = null; modoCharla(false);
  burbuja("sistema", texto);
  // botón para empezar otra: limpia la conversación anterior y arranca de nuevo
  const otra = el("div", "inicio-charla otra"); otra.id = "inicio-charla";
  const b = el("button", "boton grande", "Iniciar otra charla"); b.id = "iniciar";
  b.onclick = () => { document.querySelectorAll("#mensajes .mensaje").forEach((m) => m.remove()); iniciar(); };
  otra.append(b); $("#mensajes").append(otra);
  cargar();
}

/* ---------- conectar todo ---------- */
export function prepararCharla() {
  $("#reloj-arco").style.strokeDasharray = LARGO;
  addEventListener("popstate", () => { if (sesion) history.pushState({ charla: true }, ""); else escenas.cerrarPanel("charla"); });
  $("#iniciar").onclick = iniciar;
  $("#terminar").onclick = terminar;
  $("#novedades").onclick = () => enviar("/api/novedades", {}, "Novedades");

  $("#form").onsubmit = (e) => {
    e.preventDefault();
    const t = $("#texto").value.trim(); if (!t || ocupado) return;
    $("#texto").value = ""; $("#texto").style.height = "";
    enviar("/api/mensaje", { texto: t }, t);
  };
  $("#texto").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !matchMedia("(pointer: coarse)").matches) { e.preventDefault(); $("#form").requestSubmit(); }
  });
  $("#texto").addEventListener("input", (e) => { e.target.style.height = ""; e.target.style.height = e.target.scrollHeight + "px"; });

  // Si se cierra la página con la charla abierta, se termina sola
  // (y si el aviso no llega, el servidor la cierra por falta de latido).
  addEventListener("pagehide", () => {
    if (sesion) fetch("/api/charla/terminar", { method: "POST", keepalive: true,
      headers: { "Content-Type": "application/json", "X-Clave": clave || "" }, body: JSON.stringify({ sesion }) });
  });
  addEventListener("beforeunload", (e) => { if (sesion) { e.preventDefault(); e.returnValue = ""; } });
}
