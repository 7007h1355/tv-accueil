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
