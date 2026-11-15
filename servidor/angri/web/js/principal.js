// principal.js: el arranque. Junta el contenido de los paneles, la charla y el mundo 3D.
import { el } from "./util.js";
import { clave, pedirClave } from "./api.js";
import { cargar, pintarProximo, elegirTema } from "./panel.js";
import { prepararCharla, puedeCerrar, alAbrir } from "./charla.js";
import * as escenas from "./escenas.js";

if (!clave) pedirClave();
else {
  prepararCharla();
  // Atajos de teclado: los mismos paneles que las opciones 3D, como botones comunes.
  for (const o of [{ id: "ahora", nombre: "Ahora" }, ...escenas.OPCIONES]) {
    const b = el("button", "", o.nombre); b.type = "button";
    b.onclick = () => escenas.abrirPanel(o.id);
    document.querySelector("#atajos").append(b);
  }
  escenas.iniciar({ alElegirTema: (nombre) => elegirTema(nombre, true), alAbrir, puedeCerrar });   // carga aparte: los datos no lo esperan
  cargar();
  setInterval(() => { if (!document.hidden) cargar(); }, 20000);
  setInterval(pintarProximo, 1000);
}
