// menu.js: las opciones, como objetos que flotan en un anillo debajo de Angri.
// Cada opción tiene su forma. Tocarla abre (o cierra) su panel; la que está abierta queda encendida.
import { color, alCambiarColores, hacia, estaQuieto } from "./comun.js";

const ALTURA = -1.62;

/* Una forma distinta para cada opción, todas de un tamaño parecido. */
function forma(THREE, id) {
  const anillo = (r, g) => new THREE.TorusGeometry(r, g, 12, 32);
  switch (id) {
    case "quien":      return [new THREE.IcosahedronGeometry(.27, 0)];
    case "temas":      return [new THREE.DodecahedronGeometry(.26, 0)];
    case "preguntas":  return [anillo(.2, .075)];
    case "conexiones": return [anillo(.15, .045).translate(-.08, 0, 0), anillo(.15, .045).rotateX(Math.PI / 2).translate(.08, 0, 0)];   // dos eslabones
    case "cuaderno":   return [new THREE.BoxGeometry(.34, .42, .1)];
    case "diario":     return [new THREE.CylinderGeometry(.24, .24, .07, 32).rotateX(Math.PI / 2)];
    case "de-vos":     return [new THREE.OctahedronGeometry(.28, 0)];
    case "salud":      return [new THREE.CapsuleGeometry(.13, .2, 6, 16)];
    default:           return [new THREE.IcosahedronGeometry(.3, 1), anillo(.43, .012).rotateX(Math.PI / 2)];             // charla
  }
}

export function crearMenu(ctx, opciones) {
  const { THREE, vista } = ctx;
  const grupo = new THREE.Group(); grupo.position.y = ALTURA;
  ctx.giratorio.add(grupo);

  // la pista por donde giran: un aro finito
  const pista = new THREE.Mesh(new THREE.TorusGeometry(1, .004, 6, 128).rotateX(Math.PI / 2),
    new THREE.MeshBasicMaterial({ transparent: true, opacity: .35 }));
  grupo.add(pista);

  const items = opciones.map((o, i) => {
    const accion = { tipo: "opcion", id: o.id };
    const soporte = new THREE.Group();
    const material = new THREE.MeshStandardMaterial({ roughness: .45, flatShading: true });
    const joya = new THREE.Group();
    for (const g of forma(THREE, o.id)) joya.add(new THREE.Mesh(g, material));
    // una esfera invisible más grande, para que sea fácil de tocar con el dedo
    const blanco = new THREE.Mesh(new THREE.SphereGeometry(.5, 10, 8), new THREE.MeshBasicMaterial({ visible: false }));
    blanco.userData.accion = accion;
    soporte.add(joya, blanco);
    grupo.add(soporte);
    ctx.blancos.push(blanco);
    const rotulo = ctx.rotulos.crear(o.nombre, soporte, accion, o.especial ? "especial" : "");
    rotulo.sprite.position.y = -.5;
    return { ...o, i, soporte, joya, material, rotulo, tam: 1, luz: .15, abierto: false };
  });

  function colocar() {
    pista.scale.setScalar(vista.R);
    items.forEach((it, i) => {
      const a = i / items.length * Math.PI * 2;
      it.soporte.position.set(Math.sin(a) * vista.R, 0, Math.cos(a) * vista.R);
    });
  }
  function pintar() {
    const acento = new THREE.Color(color("--acento")), agua = new THREE.Color(color("--agua"));
    pista.material.color.set(color("--tenue"));
    for (const it of items) {
      const c = it.especial ? new THREE.Color(color("--claro")) : agua.clone().lerp(acento, it.i % 2 ? .85 : .25);
      it.material.color.copy(c); it.material.emissive.copy(it.especial ? acento : c);
    }
  }
  colocar(); pintar(); alCambiarColores(pintar);

  return {
    alCambiarTamano: colocar,
    objeto: (id) => items.find((it) => it.id === id)?.soporte,
    marcar(id, abierto) {
      const it = items.find((x) => x.id === id);
      if (it) { it.abierto = abierto; it.rotulo.elemento.classList.toggle("abierto", abierto); }
    },
    cuadro(t, dt) {
      const quieto = estaQuieto();
      for (const it of items) {
        const senalado = ctx.sobre?.tipo === "opcion" && ctx.sobre.id === it.id;
        it.tam = hacia(it.tam, senalado ? 1.3 : it.abierto ? 1.15 : 1, 9, dt);
        it.luz = hacia(it.luz, it.abierto ? .75 : senalado ? .45 : it.especial ? .35 : .14, 7, dt);
        it.joya.scale.setScalar(it.tam);
        it.material.emissiveIntensity = it.luz;
        it.rotulo.resaltado = senalado;
        if (!quieto) {
          it.joya.rotation.y += dt * (it.abierto ? .9 : .35);
          it.joya.rotation.x = Math.sin(t * .4 + it.i) * .25;
          it.joya.position.y = Math.sin(t * .8 + it.i * 1.7) * .06;
        }
      }
    },
  };
}
