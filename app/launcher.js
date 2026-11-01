
const nav = document.getElementById('tiles');
const els = TILES.map((t) => {
  const d = document.createElement('div');
  d.className = 'tile';
  d.style.setProperty('--glow', t.glow);
  d.innerHTML = '<div class="icon">' + t.icon + '</div><div><div class="label"></div><div class="sub"></div></div>';
  d.querySelector('.label').textContent = t.label;
  d.querySelector('.sub').textContent = t.sub;
  nav.appendChild(d);
  return d;
});
const focus = createFocus(TILES.length, 10000, Date.now());
const KEYS = { 37: 'left', 39: 'right', 13: 'ok' };

function paint() {
  els.forEach((e, i) => e.classList.toggle('focus', i === focus.index));
  nav.classList.toggle('asleep', !focus.visible(Date.now()));
}

function showError(el, msg) {
  const old = el.querySelector('.err');
  if (old) old.remove();
  const s = document.createElement('span');
  s.className = 'err';
  s.textContent = msg;
  el.appendChild(s);
  setTimeout(() => s.remove(), 4000);
}

document.addEventListener('keydown', (e) => {
  const k = KEYS[e.keyCode];
  if (!k) return;
  e.preventDefault();
  if (focus.key(k, Date.now()) === 'activate') {
    const tile = TILES[focus.index];
    const el = els[focus.index];
    Promise.resolve(run(tile.action)).catch((err) => {
      report('action ' + tile.id + ' : ' + err.message);
      showError(el, err.message);
    });
  }
  paint();
});
setInterval(paint, 500);
paint();
// le fond : la vidéo vient de GitHub Pages (même dépôt) ; en local, du dossier media/
const bg = document.getElementById('bg');
bg.src = location.hostname === '127.0.0.1' ? 'https://7007h1355.github.io/tv-accueil/media/sky.mp4' : '../media/sky.mp4';
bg.addEventListener('playing', () => report('vidéo lue'), { once: true });
bg.addEventListener('error', () => { report('vidéo erreur ' + (bg.error && bg.error.code)); bg.remove(); });

report('launcher prêt');
