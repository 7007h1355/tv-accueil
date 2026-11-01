// app/ est en scripts classiques (le proxy TizenBrew ne sert pas de type MIME) :
// on charge focus.js dans un contexte vm et on récupère la fonction globale.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

const ctx = {};
vm.runInNewContext(readFileSync(__dirname + '/../app/focus.js', 'utf8') + '\nthis.createFocus = createFocus;', ctx);
const { createFocus } = ctx;

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
