# Panneau de démarrage TV — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Module TizenBrew `app` qui s'ouvre au démarrage de la TV : fond trou noir (vidéo 4K en boucle + particules WebGL) et tuiles TizenTube / HDMI.

**Architecture:** Repo GitHub public `7007h1355/tv-launcher`. TizenBrew charge `package.json` et `app/` via jsdelivr (`gh/7007h1355/tv-launcher`), la vidéo vient de GitHub Pages. La logique (focus, veille des tuiles, actions) est en modules ES purs testés avec `node --test` ; le branchement TV (WebSocket TizenBrew, remote Samsung) est isolé dans `app/tv.js`.

**Tech Stack:** HTML/CSS/JS sans build (Chromium 85 de Tizen 6.5 → ES2019, pas d'optional chaining dans le code livré), WebGL 1, `node --test`, Blender + scripts Kerr (rendu offline), ffmpeg.

Spec : `docs/superpowers/specs/2026-11-01-tv-launcher-design.md`.

Faits établis (code TizenBrew 2.0.5, `service-nextgen/service/index.js`, `tizenbrew-ui/src/components/WebSocketClient.js`) :
- Service TizenBrew = WebSocket `ws://localhost:8081`, messages `{type, payload}`. `GetModules = 4` → réponse `{type:4, payload:[module…]}`. `LaunchModule = 5`, payload = l'objet module complet.
- Lancer un module `mods` comme l'UI : `send({type:5, payload:module})` puis `location.href = module.appPath` (sauf si `evaluateScriptOnDocumentStart`).
- Modules ajoutés par chemin jsdelivr : `npm/@foxreis/tizentube`, `gh/<user>/<repo>`.

---

## Fichiers

- `package.json` — métadonnées module TizenBrew.
- `app/index.html` — structure (vidéo, canvas, tuiles).
- `app/style.css` — mise en page 1920x1080, tuiles, halo de focus, fondu.
- `app/tiles.js` — liste des tuiles (données).
- `app/focus.js` — logique pure : focus gauche/droite, veille 10 s. Testé.
- `app/tv.js` — actions TV : lancer module TizenBrew, HDMI. Seul fichier qui touche `tizen`/WebSocket.
- `app/launcher.js` — colle tout : touches → focus → actions.
- `app/sky.js` — couche WebGL particules.
- `app/diag.html` — page de diagnostic (Task 1), retirée à la fin.
- `test/focus.test.js` — tests logique.
- `render/` — scripts de rendu de la vidéo (Kerr + étoile), hors `app/`.
- `docs/` — spec, plan ; GitHub Pages sert `docs/media/sky.mp4`.

---

### Task 1: Page de diagnostic sur la TV

But : savoir ce que la page d'un module voit réellement avant d'écrire le vrai code.

**Files:**
- Create: `package.json`, `app/diag.html`

- [ ] **Step 1: package.json pointant sur la page diag**

```json
{
  "name": "tv-launcher",
  "version": "0.1.0",
  "type": "module",
  "description": "Panneau de démarrage : trou noir + raccourcis",
  "packageType": "app",
  "appName": "Accueil",
  "appPath": "app/diag.html",
  "keys": ["ColorF0Red", "ColorF1Green", "ColorF2Yellow", "ColorF3Blue"]
}
```

- [ ] **Step 2: app/diag.html**

```html
<!doctype html>
<html><head><meta charset="utf-8"><title>diag</title>
<style>body{background:#000;color:#0f0;font:22px monospace;padding:40px;white-space:pre-wrap}</style>
</head><body><div id="o"></div>
<script>
var o = document.getElementById('o');
function log(s){ o.textContent += s + '\n'; }
log('UA ' + navigator.userAgent);
log('size ' + innerWidth + 'x' + innerHeight + ' dpr ' + devicePixelRatio);
log('tizen ' + typeof tizen + ' webapis ' + typeof webapis);
try { log('tvwindow ' + typeof tizen.tvwindow + ' inputdevice ' + typeof tizen.tvinputdevice); } catch(e){ log('tizen err ' + e.message); }
var gl = document.createElement('canvas').getContext('webgl');
log('webgl ' + !!gl + (gl ? ' ' + gl.getParameter(gl.RENDERER) : ''));
var v = document.createElement('video');
log('hevc ' + v.canPlayType('video/mp4; codecs="hvc1"') + ' h264 ' + v.canPlayType('video/mp4; codecs="avc1.640033"'));
var ws = new WebSocket('ws://localhost:8081');
ws.onopen = function(){ log('tb ws open'); ws.send(JSON.stringify({type:4, payload:null})); };
ws.onerror = function(){ log('tb ws ERROR'); };
ws.onmessage = function(m){ var d = JSON.parse(m.data); if (d.type === 4) d.payload.forEach(function(x){ log('module ' + x.fullName + ' ' + x.packageType + ' ' + x.appPath); }); else log('tb msg ' + d.type); };
var r = new WebSocket('ws://127.0.0.1:8001/api/v2/channels/samsung.remote.control?name=' + btoa('Accueil'));
r.onopen = function(){ log('remote 8001 open'); };
r.onmessage = function(m){ log('remote ' + m.data.slice(0, 120)); };
r.onerror = function(){ log('remote 8001 ERROR'); };
fetch('http://127.0.0.1:8001/api/v2/').then(function(x){ return x.text(); }).then(function(t){ log('rest ok ' + t.length); }, function(e){ log('rest ERR ' + e); });
document.addEventListener('keydown', function(e){ log('key ' + e.keyCode + ' ' + e.key); });
</script></body></html>
```

- [ ] **Step 3: Créer le repo public et pousser** (accord du porteur requis avant cette étape)

```bash
cd /Users/7007h1355/Projets/tv-launcher
git add package.json app/diag.html && git commit -m "feat: page de diagnostic TV"
gh repo create 7007h1355/tv-launcher --public --source . --push
```

- [ ] **Step 4: Ajouter le module dans TizenBrew et l'ouvrir**

Sur la TV : gestionnaire de modules → Add Module → `gh/7007h1355/tv-launcher`. Ouvrir « Accueil ». Le porteur lit / photographie l'écran.
Purge cache jsdelivr après chaque push : `curl -s https://purge.jsdelivr.net/gh/7007h1355/tv-launcher@main/app/diag.html`.

- [ ] **Step 5: Consigner les résultats**

Écrire dans `docs/tv-facts.md` : présence `tizen`, WebGL renderer, HEVC, réponse WS 8081 (fullName exact de TizenTube), remote 8001 (ouvert / refusé / demande d'autorisation), codes touches.
Décisions qui en découlent :
- HDMI : si remote 8001 ouvert → `KEY_HDMI1..4` ; sinon si `tizen.tvwindow` → API ; sinon tuile unique « Sources » (`KEY_SOURCE`) ou retrait des tuiles HDMI.
- Vidéo : HEVC si `canPlayType` ≠ "" sinon H.264.

```bash
git add docs/tv-facts.md && git commit -m "docs: capacités réelles de la page module sur la TV"
```

---

### Task 2: Logique de focus et veille (pure, testée)

**Files:**
- Create: `app/focus.js`, `test/focus.test.js`

- [ ] **Step 1: Test qui échoue**

```js
// test/focus.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createFocus } from '../app/focus.js';

test('gauche/droite bornés', () => {
  const f = createFocus(3, 10000);
  assert.equal(f.index, 0);
  f.key('left', 0);  assert.equal(f.index, 0);
  f.key('right', 0); f.key('right', 0); f.key('right', 0);
  assert.equal(f.index, 2);
});

test('veille après 10 s, la touche de réveil ne bouge pas le focus', () => {
  const f = createFocus(3, 10000);
  f.key('right', 0);
  assert.equal(f.visible(9999), true);
  assert.equal(f.visible(10000), false);
  const r = f.key('right', 10000);
  assert.equal(r, 'wake');
  assert.equal(f.index, 1);
  assert.equal(f.visible(10001), true);
});

test('ok renvoie la tuile active', () => {
  const f = createFocus(3, 10000);
  f.key('right', 0);
  assert.equal(f.key('ok', 1), 'activate');
  assert.equal(f.index, 1);
});
```

- [ ] **Step 2: Lancer, voir l'échec**

Run: `node --test 'test/*.test.js'` — Expected: FAIL `Cannot find module '../app/focus.js'`.

- [ ] **Step 3: Implémentation**

```js
// app/focus.js
export function createFocus(count, idleMs) {
  let last = 0;
  const f = {
    index: 0,
    visible(now) { return now - last < idleMs; },
    key(k, now) {
      const asleep = !f.visible(now);
      last = now;
      if (asleep) return 'wake';
      if (k === 'left') f.index = Math.max(0, f.index - 1);
      else if (k === 'right') f.index = Math.min(count - 1, f.index + 1);
      else if (k === 'ok') return 'activate';
      return 'move';
    },
  };
  return f;
}
```

- [ ] **Step 4: Tests verts**

Run: `node --test 'test/*.test.js'` — Expected: 3 pass (ESM grâce à `"type": "module"` du `package.json` racine ; TizenBrew ignore ce champ).

- [ ] **Step 5: Commit**

```bash
git add app/focus.js test/ && git commit -m "feat: focus des tuiles et mise en veille"
```

---

### Task 3: Tuiles, page et actions TV

**Files:**
- Create: `app/tiles.js`, `app/tv.js`, `app/launcher.js`, `app/index.html`, `app/style.css`
- Modify: `package.json` (`appPath` → `app/index.html`)

- [ ] **Step 1: app/tiles.js** (HDMI selon `docs/tv-facts.md`)

```js
export const TILES = [
  { id: 'tizentube', label: 'YouTube', action: { kind: 'module', name: 'npm/@foxreis/tizentube' } },
  { id: 'hdmi1', label: 'HDMI 1', action: { kind: 'key', key: 'KEY_HDMI1' } },
  { id: 'hdmi2', label: 'HDMI 2', action: { kind: 'key', key: 'KEY_HDMI2' } },
  { id: 'hdmi3', label: 'HDMI 3', action: { kind: 'key', key: 'KEY_HDMI3' } },
  { id: 'hdmi4', label: 'HDMI 4', action: { kind: 'key', key: 'KEY_HDMI4' } },
];
```

- [ ] **Step 2: app/tv.js**

```js
// Tout ce qui parle à la TV. Le reste de l'appli ne touche ni tizen ni WebSocket.
let tb = null;
const modules = new Promise((resolve) => {
  tb = new WebSocket('ws://localhost:8081');
  tb.onopen = () => tb.send(JSON.stringify({ type: 4, payload: null }));
  tb.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.type === 4) resolve(d.payload);
  };
  tb.onerror = () => resolve([]);
});

let remote = null;
function remoteSocket() {
  if (remote && remote.readyState <= 1) return remote;
  remote = new WebSocket('ws://127.0.0.1:8001/api/v2/channels/samsung.remote.control?name=' + btoa('Accueil'));
  return remote;
}

export async function launchModule(fullName) {
  const list = await modules;
  const mdl = list.find((m) => m.fullName === fullName);
  if (!mdl) throw new Error('module absent : ' + fullName);
  if (typeof tizen !== 'undefined') mdl.keys.forEach((k) => tizen.tvinputdevice.registerKey(k));
  tb.send(JSON.stringify({ type: 5, payload: mdl }));
  if (!mdl.evaluateScriptOnDocumentStart) location.href = mdl.appPath;
}

export function sendKey(key) {
  const ws = remoteSocket();
  const msg = JSON.stringify({ method: 'ms.remote.control', params: { Cmd: 'Click', DataOfCmd: key, Option: 'false', TypeOfRemote: 'SendRemoteKey' } });
  if (ws.readyState === 1) ws.send(msg);
  else ws.addEventListener('open', () => ws.send(msg), { once: true });
}

export function run(action) {
  if (action.kind === 'module') return launchModule(action.name);
  if (action.kind === 'key') return sendKey(action.key);
}
```

- [ ] **Step 3: app/index.html**

```html
<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Accueil</title>
<link rel="stylesheet" href="style.css"></head>
<body>
<video id="bg" autoplay muted loop playsinline></video>
<canvas id="sky"></canvas>
<nav id="tiles"></nav>
<script type="module" src="launcher.js"></script>
</body></html>
```

- [ ] **Step 4: app/style.css**

```css
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#000;font-family:system-ui,sans-serif}
#bg,#sky{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
#tiles{position:absolute;left:0;right:0;bottom:90px;display:flex;justify-content:center;gap:36px;transition:opacity .8s}
#tiles.asleep{opacity:0}
.tile{width:220px;height:124px;border-radius:22px;display:flex;align-items:center;justify-content:center;
  color:#e8ecff;font-size:30px;letter-spacing:.04em;background:rgba(10,12,24,.42);
  border:1px solid rgba(160,180,255,.18);backdrop-filter:blur(14px);transition:transform .25s,box-shadow .25s}
.tile.focus{transform:scale(1.12);box-shadow:0 0 0 2px rgba(190,210,255,.9),0 0 46px rgba(120,160,255,.55)}
.tile .err{position:absolute;bottom:-34px;font-size:18px;color:#ff9a9a}
```

- [ ] **Step 5: app/launcher.js**

```js
import { TILES } from './tiles.js';
import { createFocus } from './focus.js';
import { run } from './tv.js';

const nav = document.getElementById('tiles');
const els = TILES.map((t) => {
  const d = document.createElement('div');
  d.className = 'tile';
  d.style.position = 'relative';
  d.textContent = t.label;
  nav.appendChild(d);
  return d;
});
const focus = createFocus(TILES.length, 10000);
const KEYS = { 37: 'left', 39: 'right', 13: 'ok' };

function paint() {
  els.forEach((e, i) => e.classList.toggle('focus', i === focus.index));
  nav.classList.toggle('asleep', !focus.visible(Date.now()));
}

document.addEventListener('keydown', (e) => {
  const k = KEYS[e.keyCode];
  if (!k) return;
  e.preventDefault();
  if (focus.key(k, Date.now()) === 'activate') {
    const el = els[focus.index];
    Promise.resolve(run(TILES[focus.index].action)).catch((err) => {
      el.insertAdjacentHTML('beforeend', '<span class="err"></span>');
      el.lastChild.textContent = err.message;
    });
  }
  paint();
});
setInterval(paint, 500);
paint();
```

- [ ] **Step 6: Test local navigateur**

`python3 -m http.server -d app 8099`, ouvrir `http://localhost:8099/` dans le navigateur intégré à 1920x1080 : 5 tuiles, flèches déplacent le halo, veille à 10 s, réveil sans déplacement. Console sans erreur hors WebSocket (normal hors TV).

- [ ] **Step 7: Commit, push, purge, test TV**

```bash
git add app package.json && git commit -m "feat: tuiles TizenTube/HDMI et actions TV" && git push
curl -s https://purge.jsdelivr.net/gh/7007h1355/tv-launcher@main/package.json
```
Sur la TV : YouTube s'ouvre avec TizenTube actif (pas de pub, menu jaune), chaque HDMI bascule.

---

### Task 4: Couche WebGL (étoiles en parallaxe + poussière qui spirale)

**Files:**
- Create: `app/sky.js`
- Modify: `app/launcher.js` (ajouter `import './sky.js';`)

- [ ] **Step 1: app/sky.js**

Points WebGL 1, additifs. `HOLE` = position écran du trou dans la vidéo (réglée en Task 6).

```js
const HOLE = { x: 0.62, y: 0.42 };
const canvas = document.getElementById('sky');
const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: false });
if (gl) start();

function start() {
  canvas.width = 1920; canvas.height = 1080;
  const N = 2400;
  const data = new Float32Array(N * 4); // a: rayon0, b: angle0, c: vitesse, d: kind (0 étoile, 1 poussière)
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
      float r = mix(0.55, 0.02, life * life);
      float ang = p.y + life * 9.0 / (r + 0.15);
      pos = hole + vec2(cos(ang) * r * 0.5625, sin(ang) * r * 0.32);
      a = smoothstep(0.0, 0.15, life) * (1.0 - smoothstep(0.85, 1.0, life)) * 0.55;
      gl_PointSize = 2.5;
    } else {
      pos = vec2(fract(p.x + t * 0.0015 * p.z), fract(p.y / 6.2832));
      a = 0.35 + 0.65 * fract(sin(p.y * 91.7) * 4375.8) * (0.6 + 0.4 * sin(t * p.z * 2.0 + p.y * 40.0));
      gl_PointSize = 1.0 + 2.0 * p.z;
    }
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0); gl_Position.y *= -1.0;
  }`;
  const fs = `precision mediump float; varying float a; varying float k;
  void main(){ float d = length(gl_PointCoord - 0.5); float g = exp(-d * d * 18.0);
    vec3 c = k > 0.5 ? vec3(1.0, 0.78, 0.55) : vec3(0.8, 0.88, 1.0);
    gl_FragColor = vec4(c, a * g); }`;
  const prog = link(vs, fs);
  gl.useProgram(prog);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'p');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 4, gl.FLOAT, false, 0, 0);
  gl.uniform2f(gl.getUniformLocation(prog, 'hole'), HOLE.x, HOLE.y);
  const ut = gl.getUniformLocation(prog, 't');
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
  const t0 = performance.now();
  (function frame() {
    gl.viewport(0, 0, 1920, 1080);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(ut, (performance.now() - t0) / 1000);
    gl.drawArrays(gl.POINTS, 0, N);
    requestAnimationFrame(frame);
  })();
}

function link(vsSrc, fsSrc) {
  const p = gl.createProgram();
  for (const [type, src] of [[gl.VERTEX_SHADER, vsSrc], [gl.FRAGMENT_SHADER, fsSrc]]) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    gl.attachShader(p, s);
  }
  gl.linkProgram(p);
  return p;
}
```

- [ ] **Step 2: Compteur fps caché** — dans `launcher.js`, touche bleue (keyCode 406) affiche/masque un `<div>` fps calculé sur 60 frames.

- [ ] **Step 3: Test local** puis **TV** : ≥ 55 fps. Sinon baisser `N` par paliers de 600.

- [ ] **Step 4: Commit + push + purge**

```bash
git add app && git commit -m "feat: couche WebGL étoiles et poussière" && git push
```

---

### Task 5: Rendu de la vidéo trou noir (offline)

Réutilise la chaîne idle-game : proto Kerr numpy (lentille, spin 0.9, ISCO), `tools/houdini/tidal_star.py` + `recipes/tidalstar.json` (étoile déchiquetée en boucle), Blender pour la volumétrie. Pièges connus (mémoire idle-game-blackhole-sky) : pas de tracé grossier (anneaux), vraies dérivées du hamiltonien, |L| ≥ 0.05, direction finale = tangente.

**Files:**
- Create: `render/README.md`, `render/kerr_frames.py`, `render/encode.sh`

- [ ] **Step 1: Inventaire** — lister ce qui existe dans `/Users/7007h1355/Projets/idle-game/tools/` (houdini, blackhole_sky_proto.py) et dans le shader `Stage/BackdropBlackHole` ; décider ce qu'on porte en Python plein cadre. Consigner dans `render/README.md`.
- [ ] **Step 2: Version brouillon** — 480x270, 4 s, 24 ips. Montrer au porteur (image fixe + mp4). Itérer cadrage, couleurs, taille étoile/trou **avant** tout rendu long.
- [ ] **Step 3: Boucle sans couture** — durée = période commune (orbite du filament, rotation disque, nébuleuse en dérive cyclique). Vérifier : `ffmpeg` différence première/dernière image ≈ 0.
- [ ] **Step 4: Rendu final** 3840x2160 (ou 1920x1080 si la TV ne lit pas l'HEVC), 30 ips, ~60 s, en tâche de fond.
- [ ] **Step 5: Encodage** (`render/encode.sh`)

```bash
ffmpeg -framerate 30 -i frames/%05d.png -c:v libx265 -tag:v hvc1 -crf 20 -preset slow -pix_fmt yuv420p10le -movflags +faststart ../docs/media/sky.mp4
ffmpeg -framerate 30 -i frames/%05d.png -vf scale=1920:1080 -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p -movflags +faststart ../docs/media/sky-1080.mp4
```
Cible < 90 Mo par fichier (limite GitHub 100 Mo).

- [ ] **Step 6: Commit** (vidéos dans `docs/media/`, frames hors repo)

---

### Task 6: Brancher la vidéo, GitHub Pages, démarrage auto

**Files:**
- Modify: `app/launcher.js`, `app/sky.js` (`HOLE`)

- [ ] **Step 1: Activer Pages** (branche `main`, dossier `/docs`) :

```bash
gh api -X POST repos/7007h1355/tv-launcher/pages -f 'source[branch]=main' -f 'source[path]=/docs'
```

- [ ] **Step 2: Source vidéo selon HEVC** — dans `launcher.js` :

```js
const bg = document.getElementById('bg');
const base = 'https://7007h1355.github.io/tv-launcher/media/';
bg.src = base + (bg.canPlayType('video/mp4; codecs="hvc1"') ? 'sky.mp4' : 'sky-1080.mp4');
bg.onerror = () => bg.remove();
```

- [ ] **Step 3: Caler `HOLE`** sur la position du trou dans la vidéo (mesurée sur une image du rendu).
- [ ] **Step 4: Retirer `app/diag.html`**, push, purge jsdelivr.
- [ ] **Step 5: Démarrage auto** — TizenBrew : Autolaunch → « Accueil ». TV : Fonctions Smart → Exécution auto Smart Hub off, Exécuter auto la dernière appli on.
- [ ] **Step 6: Vérif finale** — TV éteinte au bouton, rallumée : panneau en < 10 s, vidéo + particules fluides, YouTube et HDMI OK, retour au panneau en relançant TizenBrew.
