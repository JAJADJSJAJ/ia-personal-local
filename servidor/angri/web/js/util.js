// util.js: ayudas chicas que usan el panel y la charla.

export const $ = (s) => document.querySelector(s);

export function el(tag, clase, texto) {
  const e = document.createElement(tag);
  if (clase) e.className = clase;
  if (texto != null) e.textContent = texto;
  return e;
}

export const quitarMarcas = (t) => (t || "").replace(/\*\*/g, "").replace(/\*/g, "");
export const sinMovimiento = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- tiempos ---------- */
export function hace(iso) {
  if (!iso) return "";
  const s = Math.max(0, (Date.now() - new Date(iso)) / 1000);
  if (s < 60) return "recién";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `hace ${Math.round(s / 3600)} h`;
  return `hace ${Math.round(s / 86400)} d`;
}
export function enCuanto(iso) {
  if (!iso) return "";
  const s = Math.round((new Date(iso) - Date.now()) / 1000);
  if (s <= 0) return "en un momento";
  return `en ${mmss(s)}`;
}
export const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

/** Antes las tarjetas aparecían al hacer scroll; ahora la entrada es el vuelo del panel. Se deja para no tocar cada módulo. */
export const aparecer = (nodo) => nodo;

/* ---------- tarjetas que se abren: lo abierto se mantiene al refrescar ---------- */
const abiertos = new Set();
export function desplegable(tarjeta, clave, contenido) {
  const d = el("div", "desplegable"); const dentro = el("div"); dentro.append(contenido); d.append(dentro);
  tarjeta.append(d);
  tarjeta.classList.add("tocable");
  if (abiertos.has(clave)) tarjeta.classList.add("abierto");
  tarjeta.onclick = (e) => {
    if (e.target.closest("a")) return;
    tarjeta.classList.toggle("abierto");
    tarjeta.classList.contains("abierto") ? abiertos.add(clave) : abiertos.delete(clave);
  };
}

/* ---------- guardar cosas chicas en el navegador, sin romper si no se puede ---------- */
export const guardado = {
  leer(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  poner(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
};
