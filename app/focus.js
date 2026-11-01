// Focus des tuiles et mise en veille : logique pure, l'heure est passée en argument.
function createFocus(count, idleMs, start = 0) {
  let last = start;
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
