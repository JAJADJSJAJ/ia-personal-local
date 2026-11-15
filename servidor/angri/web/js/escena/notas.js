// notas.js: un punto flotando por cada nota del cuaderno de Angri (hasta 200), repartidos
// en el espacio alrededor de ella. Giran con el mundo. Si no tiene notas, no hay ninguno.
import { colorCrudo, alCambiarColores, esOscuro, estaQuieto } from "./comun.js";

const MAXIMO = 200;

export function crearNotas(ctx) {
  const { THREE, vista } = ctx;
  // Los lugares se sortean una sola vez: una nota nueva suma un punto sin mover los demás.
  const pos = new Float32Array(MAXIMO * 3), dato = new Float32Array(MAXIMO * 3);
  for (let i = 0; i < MAXIMO; i++) {
    const u = Math.random() * 2 - 1, a = Math.random() * 6.283, r = 3.3 + Math.random() * 2.4, s = Math.sqrt(1 - u * u);
    pos.set([Math.cos(a) * s * r, u * r * .8, Math.sin(a) * s * r], i * 3);
    dato.set([.5 + Math.random(), Math.random() * 6.283, Math.random()], i * 3);   // tamaño, fase, mezcla de color
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("aDato", new THREE.BufferAttribute(dato, 3));
  geo.setDrawRange(0, 0);

  const uniforms = {
    uT: { value: 0 }, uEscala: { value: 1 }, uOpacidad: { value: .5 },
    uA: { value: colorCrudo("--acento") }, uB: { value: colorCrudo("--agua") },
  };
  const colores = () => {
    uniforms.uA.value = colorCrudo("--acento"); uniforms.uB.value = colorCrudo("--agua");
    uniforms.uOpacidad.value = esOscuro() ? .6 : .55;
  };
  colores(); alCambiarColores(colores);

  const puntos = new THREE.Points(geo, new THREE.ShaderMaterial({
    uniforms, transparent: true, depthWrite: false,
    vertexShader: `
      uniform float uT, uEscala;
      attribute vec3 aDato;
      varying float vMezcla; varying float vCerca;
      void main() {
        vec3 p = position + vec3(sin(uT * .11 + aDato.y), sin(uT * .08 + aDato.y * 1.7), cos(uT * .09 + aDato.y)) * .18;
        vec4 mv = modelViewMatrix * vec4(p, 1.);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = min(aDato.x * uEscala / -mv.z, 48.);
        vMezcla = aDato.z;
        vCerca = smoothstep(.8, 2.6, -mv.z);            // los que pasan pegados a la cámara se desvanecen
      }`,
    fragmentShader: `
      uniform vec3 uA, uB; uniform float uOpacidad;
      varying float vMezcla; varying float vCerca;
      void main() {
        float d = length(gl_PointCoord - .5);
        gl_FragColor = vec4(mix(uA, uB, vMezcla), smoothstep(.5, .1, d) * uOpacidad * vCerca);
      }`,
  }));
  puntos.frustumCulled = false;   // se mueven en el shader: three no sabe dónde están
  ctx.giratorio.add(puntos);

  return {
    cantidad(n) { geo.setDrawRange(0, Math.max(0, Math.min(MAXIMO, n | 0))); },
    alCambiarTamano() { uniforms.uEscala.value = vista.alto * Math.min(devicePixelRatio || 1, 2) * .1; },
    cuadro(t, dt) { if (!estaQuieto()) uniforms.uT.value += dt; },
  };
}
