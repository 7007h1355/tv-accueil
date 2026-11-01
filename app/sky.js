// Couche WebGL : étoiles proches en parallaxe + poussière qui spirale vers le trou, par-dessus la vidéo.
// HOLE = le trou de la vidéo (render/blackhole.py : centre 0.56, 0.56 depuis le bas -> 0.44 depuis le haut,
// disque vu presque de profil, inclinaison 0.17 rad, roulis 0.18 rad).
const HOLE = { x: 0.56, y: 0.44 };

(function () {
  const canvas = document.getElementById('sky');
  const gl = canvas.getContext('webgl', { alpha: true, antialias: false });
  if (!gl) { report('webgl absent'); return; }

  canvas.width = 1920; canvas.height = 1080;
  const N = 2400;
  // par point : rayon0 / x, angle0, vitesse, genre (0 étoile, 1 poussière)
  const data = new Float32Array(N * 4);
  for (let i = 0; i < N; i++) {
    const dust = i % 3 === 0 ? 1 : 0;
    data.set([0.05 + Math.random() * 0.9, Math.random() * 6.2832, 0.2 + Math.random(), dust], i * 4);
  }

  const vs = `attribute vec4 p; uniform float t; uniform vec2 hole; varying float a; varying float k;
  void main(){
    k = p.w;
    vec2 pos;
    if (p.w > 0.5) {
      float life = fract(t * 0.02 * p.z + p.x);
      float r = mix(0.33, 0.07, life * life);                 // du bord du disque à son bord intérieur (fraction de largeur)
      float ang = p.y + life * 7.0 / (r * 4.0 + 0.3);
      vec2 e = vec2(cos(ang) * r, sin(ang) * r * 0.17 * 1.7778); // ellipse du disque, en fractions d'écran
      e = vec2(e.x * 0.9838 + e.y * 0.1790, -e.x * 0.1790 + e.y * 0.9838);   // roulis
      pos = hole + e;
      a = smoothstep(0.0, 0.2, life) * (1.0 - smoothstep(0.8, 1.0, life)) * 0.35;
      gl_PointSize = 2.0;
    } else {
      pos = vec2(fract(p.x + t * 0.0015 * p.z), fract(p.y / 6.2832));
      a = (0.1 + 0.3 * fract(sin(p.y * 91.7) * 4375.8)) * (0.6 + 0.4 * sin(t * p.z * 2.0 + p.y * 40.0));
      gl_PointSize = 1.0 + 1.5 * p.z;
    }
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
    gl_Position.y *= -1.0;
  }`;
  const fs = `precision mediump float; varying float a; varying float k;
  void main(){
    float d = length(gl_PointCoord - 0.5);
    float g = exp(-d * d * 18.0);
    vec3 c = k > 0.5 ? vec3(1.0, 0.78, 0.55) : vec3(0.8, 0.88, 1.0);
    gl_FragColor = vec4(c, a * g);
  }`;

  const prog = gl.createProgram();
  [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]].forEach(([type, src]) => {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) report('shader ' + gl.getShaderInfoLog(s));
    gl.attachShader(prog, s);
  });
  gl.linkProgram(prog);
  gl.useProgram(prog);

  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'p');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 4, gl.FLOAT, false, 0, 0);
  gl.uniform2f(gl.getUniformLocation(prog, 'hole'), HOLE.x, HOLE.y);
  const ut = gl.getUniformLocation(prog, 't');
  gl.enable(gl.BLEND);
  // canvas prémultiplié : couleur additive, l'alpha s'accumule pour cacher la vidéo sous les points
  gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE, gl.ONE, gl.ONE);

  // fps mesuré sur 5 s, envoyé au Mac de dev
  const t0 = performance.now();
  let frames = 0, since = t0;
  (function frame(now) {
    gl.viewport(0, 0, 1920, 1080);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(ut, (performance.now() - t0) / 1000);
    gl.drawArrays(gl.POINTS, 0, N);
    frames++;
    if (now - since > 5000) { report('fps ' + (frames * 1000 / (now - since)).toFixed(1)); frames = 0; since = now; }
    requestAnimationFrame(frame);
  })(t0);
})();
