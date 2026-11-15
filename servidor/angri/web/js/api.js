// api.js: la clave y los pedidos al servidor.
import { el, guardado } from "./util.js";

export let clave = new URLSearchParams(location.search).get("clave");
if (clave) { guardado.poner("angri-clave", clave); history.replaceState(null, "", "/"); }
else clave = guardado.leer("angri-clave");

export function pedirClave() {
  document.body.replaceChildren();
  const c = el("div"); c.id = "clave";
  c.append(el("p", "", "Falta la clave. En angri, corré angri web y abrí el enlace que muestra, o pegala acá:"));
  const i = el("input"); i.autocomplete = "off";
  const b = el("button", "boton grande", "Entrar");
  b.onclick = () => { guardado.poner("angri-clave", i.value.trim()); location.reload(); };
  c.append(i, b); document.body.append(c);
}

export async function api(ruta, cuerpo, extra = {}) {
  const r = await fetch(ruta, {
    method: cuerpo ? "POST" : "GET",
    headers: { "X-Clave": clave || "", "Content-Type": "application/json" },
    body: cuerpo ? JSON.stringify(cuerpo) : undefined, ...extra,
  });
  if (r.status === 401) { pedirClave(); throw new Error("clave"); }
  const datos = await r.json();
  if (!r.ok) { const e = new Error(datos.error || "error"); e.status = r.status; throw e; }
  return datos;
}
