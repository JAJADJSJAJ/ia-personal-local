// lunas.js: los temas de Angri, como lunas que giran a su alrededor.
// Cuanto más pesa un tema, más grande es su luna y más cerca pasa. Tocar una abre ese tema.
import { color, alCambiarColores, hacia, estaQuieto } from "./comun.js";

export function crearLunas(ctx) {
  const { THREE, vista } = ctx;
  const grupo = new THREE.Group();
  ctx.giratorio.add(grupo);
  const esfera = new THREE.SphereGeometry(1, 28, 18);
  let lunas = [], firma = "", lista = [], resaltado = null;

  function armar() {
    for (const l of lunas) {
      ctx.rotulos.quitar(l.rotulo); l.material.dispose();
      ctx.blancos.splice(ctx.blancos.indexOf(l.blanco), 1);
    }
    grupo.clear(); lunas = [];
    const acento = new THREE.Color(color("--acento")), agua = new THREE.Color(color("--agua"));
    const max = Math.max(...lista.map((t) => t.peso), .01);
    lunas = lista.map((t, i) => {
      const w = t.peso / max;                                  // 0..1: cuánto pesa frente al mayor
      const accion = { tipo: "tema", nombre: t.nombre };
      const tinte = agua.clone().lerp(acento, w);
      const material = new THREE.MeshStandardMaterial({ color: tinte, emissive: tinte, emissiveIntensity: .2, roughness: .5 });
      const soporte = new THREE.Group();
      const bola = new THREE.Mesh(esfera, material);
      const radio = .1 + .14 * w;
      const blanco = new THREE.Mesh(esfera, new THREE.MeshBasicMaterial({ visible: false }));
      blanco.scale.setScalar(Math.max(.3, radio * 1.6)); blanco.userData.accion = accion;
      soporte.add(bola, blanco); grupo.add(soporte);
      ctx.blancos.push(blanco);
      const rotulo = ctx.rotulos.crear(t.nombre, soporte, accion, "tema");
      rotulo.tam = .92; rotulo.sprite.position.y = -(radio + .2);
      return { nombre: t.nombre, soporte, bola, blanco, material, rotulo, radio, tam: 1,
        orbita: .72 + .34 * (1 - w),                           // fracción del radio del anillo
        altura: .25 + .8 * ((i * .618) % 1),
        angulo: i * 2.39996, paso: .035 + .03 * ((i * .37) % 1) };
    });
  }

  alCambiarColores(armar);

  return {
    /** temas: [{nombre, peso}]. Si no cambió nada, no se rearma. */
    poner(temas) {
      const nueva = JSON.stringify(temas);
      if (nueva === firma) return;
      firma = nueva; lista = temas; armar();
    },
    resaltar(nombre) { resaltado = nombre; },
    cuadro(t, dt) {
      for (const l of lunas) {
        if (!estaQuieto()) l.angulo += dt * l.paso;
        const r = vista.R * l.orbita;
        l.soporte.position.set(Math.sin(l.angulo) * r, l.altura, Math.cos(l.angulo) * r);
        const senalada = l.nombre === resaltado || (ctx.sobre?.tipo === "tema" && ctx.sobre.nombre === l.nombre);
        l.tam = hacia(l.tam, senalada ? 1.45 : 1, 9, dt);
        l.bola.scale.setScalar(l.radio * l.tam);
        l.material.emissiveIntensity = senalada ? .6 : .2;
        l.rotulo.resaltado = senalada;
      }
    },
  };
}
