// orbe.js: Angri como una forma blanda que respira, en el centro del mundo.
// El ritmo sale de lo que está haciendo. Tocarla abre el panel "Ahora".
import { colorCrudo, alCambiarColores, estaQuieto, hacia, RUIDO } from "./comun.js";

/* Para cada situación: qué tan rápido se mueve, cuánto se deforma y cuánto brilla. */
const RITMOS = {
  activa:    { vel: 1.0,  amp: .17, brillo: 1.0 },
  charlando: { vel: 1.5,  amp: .21, brillo: 1.05 },
  esperando: { vel: .45,  amp: .10, brillo: .97 },
  descanso:  { vel: .35,  amp: .08, brillo: .94 },
  durmiendo: { vel: .16,  amp: .05, brillo: .8 },
  pausa:     { vel: .10,  amp: .04, brillo: .78 },
};

export function crearOrbe(ctx) {
  const { THREE } = ctx;
  const uniforms = {
    uT: { value: 0 }, uAmp: { value: .1 }, uBrillo: { value: 1 },
    uA: { value: colorCrudo("--orbe-a") }, uB: { value: colorCrudo("--orbe-b") }, uClaro: { value: colorCrudo("--claro") },
  };
  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: `
      uniform float uT, uAmp;
      varying vec3 vN; varying vec3 vV;
      ${RUIDO}
      vec3 mover(vec3 d) {            // d: dirección desde el centro
        float n = ruido(d * 1.25 + vec3(0., uT * .30, uT * .18)) * .72 + ruido(d * 2.6 - vec3(uT * .22)) * .28;
        return d * (1. + n * uAmp);
      }
      void main() {
        vec3 d = normalize(position);
        vec3 p = mover(d);
        // la normal se recalcula mirando dos puntos vecinos, para que la luz siga la forma
        vec3 t = normalize(cross(d, abs(d.y) < .95 ? vec3(0., 1., 0.) : vec3(1., 0., 0.)));
        vec3 b = cross(d, t);
        vec3 n = normalize(cross(mover(normalize(d + t * .02)) - p, mover(normalize(d + b * .02)) - p));
        vec4 mv = modelViewMatrix * vec4(p, 1.);
        vN = normalMatrix * n; vV = -mv.xyz;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      uniform vec3 uA, uB, uClaro; uniform float uBrillo;
      varying vec3 vN; varying vec3 vV;
      void main() {
        vec3 n = normalize(vN), v = normalize(vV);
        float luz = dot(n, normalize(vec3(-.45, .75, .55))) * .5 + .5;
        float borde = pow(1. - max(dot(n, v), 0.), 2.4);
        vec3 c = mix(uB, uA, smoothstep(.15, .85, luz));
        c = mix(c, uClaro, pow(luz, 6.) * .32 + borde * .22);
        gl_FragColor = vec4(c * uBrillo, 1.);
      }`,
  });
  const malla = new THREE.Mesh(new THREE.IcosahedronGeometry(1, 20), material);
  malla.userData.accion = { tipo: "orbe" };
  ctx.giratorio.add(malla);
  ctx.blancos.push(malla);

  // un halo suave detrás, siempre de cara a la cámara
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: mancha(THREE), transparent: true, depthWrite: false, opacity: .5 }));
  halo.scale.setScalar(4.4); halo.renderOrder = -1;
  ctx.scene.add(halo);

  const colores = () => {
    uniforms.uA.value = colorCrudo("--orbe-a"); uniforms.uB.value = colorCrudo("--orbe-b"); uniforms.uClaro.value = colorCrudo("--claro");
    halo.material.color.set(getComputedStyle(document.documentElement).getPropertyValue("--acento").trim());
  };
  colores(); alCambiarColores(colores);

  let meta = RITMOS.esperando, vel = meta.vel, tam = 1;
  return {
    malla,
    estado(tipo) { meta = RITMOS[tipo] || RITMOS.esperando; },
    cuadro(t, dt) {
      const lento = estaQuieto() ? .3 : 1;
      vel = hacia(vel, meta.vel, 2.2, dt);               // los cambios de ritmo llegan de a poco
      uniforms.uAmp.value = hacia(uniforms.uAmp.value, meta.amp, 2.2, dt);
      uniforms.uBrillo.value = hacia(uniforms.uBrillo.value, meta.brillo, 2.2, dt);
      uniforms.uT.value += dt * vel * lento;
      tam = hacia(tam, ctx.sobre?.tipo === "orbe" ? 1.06 : 1, 8, dt);   // crece un poquito al señalarla
      malla.scale.setScalar(tam);
      halo.material.opacity = .38 + .14 * Math.sin(t * vel * 1.3) * lento;
    },
  };
}

/** Una mancha redonda que se desvanece hacia el borde (para el halo). */
function mancha(THREE) {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d"), d = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  d.addColorStop(0, "rgba(255,255,255,.9)"); d.addColorStop(.35, "rgba(255,255,255,.35)"); d.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = d; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
