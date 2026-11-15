// panel.js: el contenido de los paneles. Solo LEE: pide el estado cada 20 segundos y lo dibuja.
// (Los paneles en sí, que vuelan y se arrastran, están en js/escena/paneles.js.)
import { $, el, quitarMarcas, hace, enCuanto, aparecer, desplegable, sinMovimiento } from "./util.js";
import { api } from "./api.js";
import * as escenas from "./escenas.js";

const NOMBRE_ACT = { azar: "leyendo", objetivo: "investigando", repasar: "repasando", conectar: "conectando",
  pensar: "pensando", descansar: "descansando", falla: "con fallas" };
let primeraVez = true, proximoIso = null;

const vacio = (texto) => el("p", "vacio", texto);

/* ---------- 01 ahora ---------- */
function renderAhora(s) {
  const si = s.situacion;
  escenas.estado(si.tipo);
  const que = si.texto + (si.tipo === "activa" ? "…" : "");
  $("#que").textContent = que; $("#que-panel").textContent = que;        // en el cartel de arriba y en el panel
  let detalle = si.detalle ? (si.actividad === "azar" ? `«${si.detalle}»` : si.detalle) : "";
  if (si.tipo === "esperando" && si.ultimo) detalle = `Lo último: ${si.ultimo.resultado || si.ultimo.actividad}`;
  if (si.tipo === "charlando") detalle = "Está con vos en la charla.";
  $("#detalle").textContent = detalle; $("#detalle-panel").textContent = detalle;
  const meta = $("#meta"); meta.replaceChildren();
  const item = (etq, val) => { const sp = el("span"); sp.append(etq + " "); sp.append(el("b", "", val)); meta.append(sp); };
  if (si.desde) item("Empezó", hace(si.desde));
  if (si.tipo === "esperando" && si.ultimo) item("Terminó", hace(si.ultimo.fecha));
  proximoIso = s.proximo;
  if (s.proximo && !["charlando", "pausa", "durmiendo"].includes(si.tipo)) { const sp = el("span"); sp.id = "prox"; meta.append(sp); }
  pintarProximo();
}
export function pintarProximo() {
  const sp = $("#prox"); if (!sp) return;
  sp.replaceChildren("Próximo ciclo ", el("b", "", enCuanto(proximoIso)));
}

function animarNumero(nodo, hasta) {
  const desde = Number(nodo.dataset.v || 0); nodo.dataset.v = hasta;
  if (desde === hasta || sinMovimiento()) { nodo.textContent = hasta; return; }
  const t0 = performance.now(), dur = 700;
  const paso = (t) => {
    const p = Math.min(1, (t - t0) / dur);
    nodo.textContent = Math.round(desde + (hasta - desde) * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}
function renderCifras(s) {
  const c = $("#cifras");
  const datos = [["lecturas", s.cifras.lecturas, "lecturas en total"], ["hoy", s.cifras.lecturas_hoy, "lecturas hoy"],
    ["notas", s.cifras.notas, "notas respaldadas"], ["preguntas", s.cifras.preguntas, "preguntas abiertas"]];
  if (!c.children.length) datos.forEach(([k], i) => {
    const d = aparecer(el("div", "pieza cifra"), i); d.append(el("b"), el("span")); d.dataset.k = k; c.append(d);
  });
  datos.forEach(([k, v, t]) => { const d = c.querySelector(`[data-k="${k}"]`); animarNumero(d.querySelector("b"), v); d.querySelector("span").textContent = t; });
  $("#dias").textContent = s.cifras.dias ? `día ${s.cifras.dias}` : "";
  escenas.notas(s.cifras.notas);
  const hoy = $("#hoy"); hoy.replaceChildren();
  Object.entries(s.actividades_hoy || {}).sort((a, b) => b[1] - a[1]).forEach(([m, n]) =>
    hoy.append(el("span", "etiqueta" + (m === "falla" ? "" : m === "descansar" ? " agua" : " acento"), `${n} ${NOMBRE_ACT[m] || m}`)));
  if (s.mensajes_sin_leer) hoy.append(el("span", "etiqueta acento", `${s.mensajes_sin_leer} cosa${s.mensajes_sin_leer > 1 ? "s" : ""} para contarte`));
}

/* ---------- 02 quién es ---------- */
function renderQuien(s) {
  const c = $("#quien-cuerpo"); c.replaceChildren();
  if (s.quien_soy) {
    const q = aparecer(el("div", "quien"));
    q.append(el("p", "", s.quien_soy));
    const pie = el("div", "pie");
    if (s.genero) pie.append(el("span", "", `Eligió que hablen de Angri ${s.genero.valor === "neutro" ? "sin marcar género" : "en " + s.genero.valor}`));
    q.append(pie); c.append(q);
  } else c.append(vacio("Todavía no escribió sobre sí. Lo hace por primera vez cuando duerma (a las 4 de la mañana)."));
  if (s.resumen) {
    const r = aparecer(el("div", "pieza resumen"), 1);
    r.append(el("h3", "", `Su resumen del ${s.resumen.fecha.split("-").reverse().slice(0, 2).join("/")}`), el("p", "", s.resumen.texto));
    c.append(r);
  }
}

/* ---------- 03 temas ---------- */
function renderTemas(s) {
  const c = $("#temas-cuerpo"); c.replaceChildren();
  escenas.temas(s.temas.map((t) => ({ nombre: t.nombre, peso: t.peso })));
  if (!s.temas.length) return c.append(vacio("Ningún tema todavía. Aparecen solos cuando junta tres notas parecidas."));
  const max = Math.max(...s.temas.map((t) => t.peso), 0.01);
  s.temas.forEach((t, i) => {
    const d = aparecer(el("div", "pieza tema"), i);
    d.dataset.tema = t.nombre;
    const fila = el("div", "fila"); fila.append(el("h3", "", t.nombre), el("span", "n", `${t.notas} notas`));
    const b = el("div", "barra-peso"); const relleno = el("div"); b.append(relleno);
    d.append(fila, b);
    requestAnimationFrame(() => requestAnimationFrame(() => { relleno.style.width = `${Math.max(6, 100 * t.peso / max)}%`; }));
    desplegable(d, "tema:" + t.nombre, el("div", "entendi", t.entendi || "Todavía no escribió lo que entendió de este tema."));
    d.onpointerenter = () => escenas.resaltarTema(t.nombre);
    d.onpointerleave = () => escenas.resaltarTema(null);
    c.append(d);
  });
}
/** Desde la constelación: al pasar por un tema se marca su tarjeta; al tocarlo, se abre. */
export function elegirTema(nombre, abrir) {
  document.querySelectorAll(".tema").forEach((d) => {
    const es = d.dataset.tema === nombre;
    d.classList.toggle("resaltada", es);
    if (es && abrir) {
      if (!d.classList.contains("abierto")) d.click();
      d.scrollIntoView({ block: "nearest", behavior: sinMovimiento() ? "auto" : "smooth" });
    }
  });
}

/* ---------- 04 preguntas ---------- */
function renderPreguntas(s) {
  const c = $("#preguntas-cuerpo"); c.replaceChildren();
  if (s.investigando.length) {
    const g = el("div", "lista");
    s.investigando.forEach((o, i) => {
      const d = aparecer(el("div", "pieza investigacion"), i);
      d.append(el("p", "", quitarMarcas(o.pregunta)));
      const p = el("div", "pasos"); for (let k = 0; k < o.presupuesto; k++) p.append(el("i", k < o.gastado ? "lleno" : ""));
      d.append(p, el("div", "pasos-txt", `investigando · ${o.gastado} de ${o.presupuesto} lecturas`));
      g.append(d);
    });
    c.append(g);
  }
  if (s.preguntas.length) {
    const ul = el("ul", "lista-preguntas");
    s.preguntas.forEach((p, i) => ul.append(aparecer(el("li", "", quitarMarcas(p.texto)), i)));
    c.append(ul);
  }
  if (!s.investigando.length && !s.preguntas.length) c.append(vacio("Sin preguntas por ahora. Le surgen al leer."));
  if (s.cerradas.length) {
    c.append(el("h3", "subtitulo", "Cerradas"));
    const g = el("div", "lista");
    const ETQ = { respondido: ["respondida", "agua"], agotado: ["sin respuesta", ""], sin_presupuesto: ["se le acabaron las lecturas", ""], fallido: ["falló", ""] };
    s.cerradas.forEach((o, i) => {
      const d = aparecer(el("div", "pieza cerrada"), i);
      const etq = ETQ[o.estado] || [o.estado, ""];
      const q = el("p", "q", quitarMarcas(o.pregunta) + " "); q.append(el("span", "etiqueta " + etq[1], etq[0]));
      d.append(q); if (o.respuesta) d.append(el("p", "r", o.respuesta));
      g.append(d);
    });
    c.append(g);
  }
}

/* ---------- 05 conexiones ---------- */
const ICONO_UNION = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 17H7A5 5 0 0 1 7 7h2M15 7h2a5 5 0 0 1 0 10h-2M8 12h8"/></svg>';
function renderConexiones(s) {
  const c = $("#conexiones-cuerpo"); c.replaceChildren();
  if (!s.conexiones.length) return c.append(vacio("Todavía no unió dos cosas. Empieza cuando tenga varias notas."));
  s.conexiones.forEach((x, i) => {
    const d = aparecer(el("div", "pieza conexion"), i);
    const par = el("div", "par"); par.append(el("span", "", x.a));
    par.insertAdjacentHTML("beforeend", ICONO_UNION);
    par.append(el("span", "", x.b));
    d.append(par, el("p", "", x.texto)); c.append(d);
  });
}

/* ---------- 06 cuaderno ---------- */
function renderNotas(s) {
  const c = $("#notas-cuerpo"); c.replaceChildren();
  if (!s.notas.length) return c.append(vacio("El cuaderno está vacío. Se llena con cada lectura que pasa los controles."));
  const caja = el("div", "notas");
  s.notas.forEach((n, i) => {
    const d = aparecer(el("article", "pieza nota"), i);
    const de = el("div", "de"); de.append(el("span", "", hace(n.fecha)));
    if (n.estado === "confirmada") de.append(el("span", "etiqueta agua", "confirmada"));
    d.append(de, el("h3", "", n.titulo), el("p", "texto", n.resumen));
    const extra = el("div"); extra.append(el("blockquote", "cita", "“" + n.cita + "”"));
    if (n.url) { const a = el("a", "fuente", "Leer en Wikipedia ↗"); a.href = n.url; a.target = "_blank"; a.rel = "noopener noreferrer"; extra.append(a); }
    desplegable(d, "nota:" + n.titulo, extra);
    caja.append(d);
  });
  c.append(caja);
}

/* ---------- 07 diario ---------- */
function renderDiario(s) {
  const c = $("#diario-cuerpo"); c.replaceChildren();
  if (!s.diario.length) return c.append(vacio("Todavía no escribió nada."));
  const ul = el("ul", "linea-tiempo"); let dia = null;
  const hoyIso = new Date().toISOString().slice(0, 10);
  s.diario.forEach((l, i) => {
    if (l.fecha !== dia) {
      dia = l.fecha;
      const li = el("li", "dia-fila"); li.append(el("span", "dia", l.fecha === hoyIso ? "hoy" : l.fecha.split("-").reverse().join("/")));
      ul.append(li);
    }
    const li = aparecer(el("li"), i); li.append(el("time", "", l.hora), el("p", "", l.texto)); ul.append(li);
  });
  c.append(ul);
}

/* ---------- 08 lo que le contaste ---------- */
function renderDeFran(s) {
  const c = $("#defran-cuerpo"); c.replaceChildren();
  if (!s.de_fran.length) return c.append(vacio("Cuando te pregunte algo y le contestes en la charla, aparece acá. Lo guarda como lo que le contaste vos, aparte de lo que lee."));
  s.de_fran.forEach((x, i) => {
    const d = aparecer(el("div", "pieza de-fran"), i);
    d.append(el("p", "q", "Le preguntó: " + x.pregunta), el("blockquote", "", "“" + x.respuesta + "”"));
    c.append(d);
  });
}

/* ---------- 09 salud ---------- */
function renderSalud(s) {
  const c = $("#salud-cuerpo"); c.replaceChildren();
  if (!s.vigilancia.length) c.append(aparecer(el("div", "pieza", "Todo normal: no hay ningún ajuste activo.")));
  s.vigilancia.forEach((v, i) => c.append(aparecer(el("div", "pieza", `Ajuste activo hasta las ${v.hasta.slice(11, 16)}: ${v.motivo}`), i)));
}

/* ---------- pedir y dibujar ---------- */
export async function cargar() {
  try {
    const s = await api("/api/estado");
    renderAhora(s); renderCifras(s);
    // Si hay un tema o una nota abiertos, no se redibuja el resto: se cerraría lo que estás leyendo.
    if (primeraVez || !document.querySelector(".tema.abierto, .nota.abierto")) {
      renderQuien(s); renderTemas(s); renderPreguntas(s); renderConexiones(s); renderNotas(s); renderDiario(s); renderDeFran(s); renderSalud(s);
    }
    primeraVez = false;
    $("#actualizado").textContent = "actualizado " + new Date().toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
  } catch (e) { if (e.message !== "clave") $("#que").textContent = "Sin conexión con Angri"; }
}
