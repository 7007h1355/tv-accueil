"""Fond du panneau TV : trou noir de Kerr qui déchiquette une étoile, nébuleuse et étoiles derrière.

Rendu offline sur GPU (moderngl, OpenGL 4.1). La caméra et le trou ne bougent pas :
  1. bake (une fois) : chaque pixel trace son photon à rebours dans le champ de Kerr (traceur porté du jeu
     idle-game, Assets/Resources/Stage/BackdropBlackHole.shader : hamiltonien séparable, RK4) -> où il
     s'échappe (plan lointain, en rs), ses deux traversées du plan du disque, capturé ou non ;
  2. frame : lit le bake, dessine le ciel lentillé, le disque (chaleur, Doppler, Kepler), l'étoile étirée
     et son flux, à l'instant t. Boucle : fondu de F secondes entre t et t + T.

  python render/blackhole.py still out.png [--w 960 --h 540 --t 0]
  python render/blackhole.py video out.mp4 [--w 3840 --h 2160 --seconds 60 --fps 30]
"""
import argparse
import subprocess
import sys
from pathlib import Path

import moderngl
import numpy as np

HERE = Path(__file__).parent

VERT = """
#version 410
in vec2 pos;
out vec2 uv;
void main() { uv = pos * 0.5 + 0.5; gl_Position = vec4(pos, 0.0, 1.0); }
"""

BAKE = """
#version 410
in vec2 uv;
layout(location = 0) out vec4 outA;   // position finale du rayon (rs, repère du trou), capturé
layout(location = 3) out vec4 outD;   // direction finale du rayon
layout(location = 1) out vec4 outB;   // 1re traversée du disque : r (rs), phi, g (Doppler), 1
layout(location = 2) out vec4 outC;   // 2e traversée
uniform vec2 size;      // px
uniform vec4 hole;      // centre x, y (fractions), rs en px, roulis
uniform vec4 geo;       // inclinaison, rin, rout, spin a
uniform vec2 band;      // lignes du bake dessinées maintenant (0..1)

void Deriv(float a, float L, float r, float th, float pr, float pth,
           out float dr, out float dth, out float dphi, out float dpr, out float dpth) {
    float sn = sin(th), cs = cos(th), s2 = max(sn * sn, 1e-8);
    float S = r * r + a * a * cs * cs, De = r * r - 2.0 * r + a * a;
    float P = r * r + a * a - a * L;
    float F = De * pr * pr + pth * pth - P * P / De + (L - a * s2) * (L - a * s2) / s2;
    float dFr = (2.0 * r - 2.0) * pr * pr - (4.0 * r * P / De - P * P * (2.0 * r - 2.0) / (De * De));
    float dFt = 2.0 * sn * cs * (a * a - L * L / (s2 * s2));
    dr = De * pr / S;
    dth = pth / S;
    dphi = (a * P / De + L / s2 - a) / S;
    dpr = -(dFr / (2.0 * S) - F * r / (S * S));
    dpth = -(dFt / (2.0 * S) + F * a * a * sn * cs / (S * S));
}

vec3 Cart(float a, float r, float th, float ph) {
    float rho = sqrt(r * r + a * a);
    return vec3(rho * sin(th) * cos(ph), rho * sin(th) * sin(ph), r * cos(th));
}

vec3 Velocity(float a, float L, float r, float th, float ph, float pr, float pth) {
    float dr, dth, dph, u, w;
    Deriv(a, L, r, th, pr, pth, dr, dth, dph, u, w);
    float rho = sqrt(r * r + a * a), st = sin(th), ct = cos(th), sp = sin(ph), cp = cos(ph);
    vec3 v = dr * vec3(r / rho * st * cp, r / rho * st * sp, ct) + dth * vec3(rho * ct * cp, rho * ct * sp, -r * st)
           + dph * vec3(-rho * st * sp, rho * st * cp, 0.0);
    return normalize(v + 1e-12);
}

void main() {
    if (uv.y < band.x || uv.y > band.y) discard;
    // pixel -> repère du trou en rs (y vers le haut, roulis défait)
    vec2 px = uv * size;
    vec2 d0 = (px - hole.xy * size) / hole.z;
    float c0r = cos(hole.w), s0r = sin(hole.w);
    vec2 b = vec2(d0.x * c0r + d0.y * s0r, -d0.x * s0r + d0.y * c0r);

    const float D = 80.0;
    float t = geo.x, a = clamp(geo.w, 0.0, 0.998);
    vec3 n = vec3(0.0, cos(t), sin(t));
    vec3 e1 = vec3(1.0, 0.0, 0.0), e2 = cross(n, e1);
    vec3 p0 = vec3(b, D) * 2.0, dv = vec3(0.0, 0.0, -1.0);
    vec3 x = vec3(dot(p0, e1), dot(p0, e2), dot(p0, n)), d = vec3(dot(dv, e1), dot(dv, e2), dot(dv, n));
    float R2 = dot(x, x), bb = R2 - a * a;
    float r = sqrt(0.5 * (bb + sqrt(bb * bb + 4.0 * a * a * x.z * x.z)));
    float th = acos(clamp(x.z / r, -1.0, 1.0)), ph = atan(x.y, x.x);
    float rho = sqrt(r * r + a * a), st = sin(th), ct = cos(th);
    vec3 dxdr = vec3(r / rho * st * cos(ph), r / rho * st * sin(ph), ct);
    vec3 dxdt = vec3(rho * ct * cos(ph), rho * ct * sin(ph), -r * st);
    float pth = dot(dxdt, d), L = x.x * d.y - x.y * d.x;
    // un rayon par l'axe (L = 0) est raide : |L| >= 0.05 (sinon une ligne pointillée au-dessus de l'ombre)
    L = (L < 0.0 ? -1.0 : 1.0) * max(abs(L), 0.1);
    float Q = pth * pth + ct * ct * (L * L / max(st * st, 1e-8) - a * a);
    float De = r * r - 2.0 * r + a * a;
    float Rr = (r * r + a * a - a * L) * (r * r + a * a - a * L) - De * ((L - a) * (L - a) + Q);
    float pr = sign(dot(dxdr, d)) * sqrt(max(Rr, 0.0)) / De;
    float r0 = r, rh = 1.0 + sqrt(1.0 - a * a);
    vec3 cprev = x, vel = d;
    bool escaped = false, captured = false;
    vec4 hit1 = vec4(0.0), hit2 = vec4(0.0);
    int hits = 0;
    for (int k = 0; k < 3000; k++) {
        float s2 = max(sin(th) * sin(th), 1e-8);
        float h = max(min(0.03 * max(r - rh, 0.02), 0.08 * r * r * s2 / (abs(L) + 1e-6)), 5e-4);
        float k1r, k1t, k1p, k1a, k1b, k2r, k2t, k2p, k2a, k2b, k3r, k3t, k3p, k3a, k3b, k4r, k4t, k4p, k4a, k4b;
        Deriv(a, L, r, th, pr, pth, k1r, k1t, k1p, k1a, k1b);
        Deriv(a, L, r + 0.5 * h * k1r, th + 0.5 * h * k1t, pr + 0.5 * h * k1a, pth + 0.5 * h * k1b, k2r, k2t, k2p, k2a, k2b);
        Deriv(a, L, r + 0.5 * h * k2r, th + 0.5 * h * k2t, pr + 0.5 * h * k2a, pth + 0.5 * h * k2b, k3r, k3t, k3p, k3a, k3b);
        Deriv(a, L, r + h * k3r, th + h * k3t, pr + h * k3a, pth + h * k3b, k4r, k4t, k4p, k4a, k4b);
        float nr = r + h / 6.0 * (k1r + 2.0 * k2r + 2.0 * k3r + k4r);
        float nth = th + h / 6.0 * (k1t + 2.0 * k2t + 2.0 * k3t + k4t);
        float nph = ph + h / 6.0 * (k1p + 2.0 * k2p + 2.0 * k3p + k4p);
        pr += h / 6.0 * (k1a + 2.0 * k2a + 2.0 * k3a + k4a);
        pth += h / 6.0 * (k1b + 2.0 * k2b + 2.0 * k3b + k4b);
        vec3 c = Cart(a, nr, nth, nph);
        vel = Velocity(a, L, nr, nth, nph, pr, pth);
        float c0 = cos(th), c1 = cos(nth);
        if (c0 * c1 < 0.0 && hits < 2) {
            float f = c0 / (c0 - c1);
            float rc = mix(r, nr, f), pc = mix(ph, nph, f);
            vec3 p = vec3(cos(pc), sin(pc), 0.0) * (sin(mix(th, nth, f)) < 0.0 ? -1.0 : 1.0);
            float rs = rc * 0.5;
            vec3 tang = vec3(-p.y, p.x, 0.0);
            float beta = min(sqrt(0.5 / max(rs - 1.0, 0.1)), 0.6);
            float g = sqrt(1.0 - beta * beta) / (1.0 - beta * dot(tang, vel));
            vec4 hh = vec4(rs, atan(p.y, p.x), g, 1.0);
            if (hits == 0) hit1 = hh; else hit2 = hh;
            hits++;
        }
        r = nr; th = nth; ph = nph; cprev = c;
        if (r < rh * 1.02) { captured = true; break; }
        if (r > r0 * 1.02 && pr > 0.0) { escaped = true; break; }
    }
    captured = captured || !escaped;
    vec3 pos = (cprev.x * e1 + cprev.y * e2 + cprev.z * n) * 0.5;
    vec3 v = vel.x * e1 + vel.y * e2 + vel.z * n;
    outA = vec4(pos, captured ? 1.0 : 0.0);
    outD = vec4(v, 1.0);
    outB = hit1;
    outC = hit2;
}
"""

FRAME = """
#version 410
in vec2 uv;
out vec4 frag;
uniform sampler2D bakeA, bakeB, bakeC, bakeD;
uniform vec2 size;
uniform vec4 hole;      // centre x, y (fractions), rs en px, roulis
uniform vec4 geo;       // inclinaison, rin, rout, a
uniform vec4 star;      // r (rs), phi, rayon (rs), étirement vers le trou
uniform float dsrc;     // profondeur du ciel derrière le trou (rs) : plus loin = lentille plus forte
uniform float t0;       // temps de la boucle (s)
uniform float loopT;    // période
uniform float fadeF;    // durée du fondu

// ---- bruit ----
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float hash3(vec3 p) { p = fract(p * 0.1031); p += dot(p, p.yzx + 33.33); return fract((p.x + p.y) * p.z); }
float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
float vnoise3(vec3 p) {
    vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
    float n000 = hash3(i), n100 = hash3(i + vec3(1,0,0)), n010 = hash3(i + vec3(0,1,0)), n110 = hash3(i + vec3(1,1,0));
    float n001 = hash3(i + vec3(0,0,1)), n101 = hash3(i + vec3(1,0,1)), n011 = hash3(i + vec3(0,1,1)), n111 = hash3(i + vec3(1,1,1));
    return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y), mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 7; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s; }
float fbm3(vec3 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise3(p); p = p * 2.07 + 11.3; a *= 0.5; } return s; }

// ---- ciel : nébuleuse + étoiles, en coordonnées du plan source (rs) ----
vec3 starLayer(vec2 p, float cell, float density, float t) {
    vec2 g = p / cell, i = floor(g), f = fract(g);
    vec3 col = vec3(0.0);
    for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
        vec2 o = vec2(x, y), id = i + o;
        if (hash(id) > density) continue;
        vec2 c = (o + vec2(hash(id + 3.1), hash(id + 7.7)) - f) * cell;
        float m = pow(hash(id + 9.3), 8.0);                   // beaucoup de faibles, peu de brillantes
        float tw = 0.8 + 0.2 * sin(t * (0.7 + 2.0 * hash(id + 1.7)) + 6.28 * hash(id + 5.5));
        float d2 = dot(c, c);
        float core = exp(-d2 / 0.0018) * (0.25 + 6.0 * m) * tw;
        float halo = exp(-d2 / (0.01 + 0.12 * m)) * 0.3 * m;
        float temp = hash(id + 2.2);
        vec3 tint = temp < 0.2 ? vec3(1.0, 0.7, 0.5) : temp < 0.6 ? vec3(1.0, 0.96, 0.92) : vec3(0.68, 0.8, 1.0);
        col += tint * (core + halo);
    }
    return col;
}

vec3 sky(vec2 p, float t) {
    vec2 q = p * 0.045 + vec2(3.7, 1.3);
    vec2 w = vec2(fbm(q * 1.1 + 4.0), fbm(q * 1.1 + 9.0));
    float n1 = fbm(q * 1.4 + w * 2.0);
    float n2 = fbm(q * 2.2 - w * 1.4 + 21.0);
    float dust = smoothstep(0.45, 0.72, fbm(q * 3.2 + w * 2.6 + 40.0));
    vec3 neb = vec3(0.0);
    neb += vec3(0.26, 0.05, 0.40) * pow(smoothstep(0.48, 0.92, n1), 2.4) * 1.0;            // violet
    neb += vec3(0.02, 0.20, 0.36) * pow(smoothstep(0.45, 0.92, n2), 2.0) * 1.2;           // bleu-sarcelle
    neb += vec3(0.75, 0.25, 0.10) * pow(smoothstep(0.66, 0.95, n1 * n2 * 1.9), 2.4) * 1.1; // cœurs chauds
    neb *= 1.0 - 0.85 * dust;
    vec3 s = starLayer(p, 0.7, 0.45, t) * 0.35 + starLayer(p + 31.0, 2.2, 0.22, t) * 0.7 + starLayer(p + 77.0, 7.0, 0.18, t) * 1.3;
    s *= 1.0 - 0.7 * dust;
    return neb + s;
}

// ---- disque + flux, pour une traversée h du plan ----
vec4 diskLight(vec4 h, float t) {
    if (h.w < 0.5) return vec4(0.0);
    float r = h.x, phi = h.y, g = h.z;
    float rin = geo.y, rout = geo.z;
    float x = max(r / rin, 1e-3);
    float temp = pow(x, -0.75) * pow(clamp(1.0 - sqrt(1.0 / x), 0.0, 1.0), 0.25) * 2.2;
    float I = temp * pow(max(g, 0.0), 3.5) * sqrt(clamp(1.0 - 1.0 / max(r, 1e-3), 0.0, 1.0));
    // rotation de Kepler (le dedans plus vite) en flow-map : deux phases de 6 s en fondu, le cisaillement reste borné
    // (sinon le bruit s'enroule sans fin en anneaux de vinyle)
    float omega = 0.22 * pow(rin / max(r, 1e-3), 1.5);
    float lr = log(r) * 2.2;
    float st = 0.0;
    for (int k = 0; k < 2; k++) {
        float ph = t / 6.0 + float(k) * 0.5;
        float fr = fract(ph), cyc = floor(ph);
        float ang = phi + (fr - 0.5) * 6.0 * omega * 6.2831853;
        vec2 pa = vec2(cos(ang), sin(ang));
        vec3 o = vec3(cyc * 7.31 + float(k) * 3.7);
        float n = fbm3(vec3(pa * 1.8, lr) + o) * 1.0 + fbm3(vec3(pa * 5.5, lr * 2.0) + o + 5.0) * 0.55 - 0.6;
        st += n * (1.0 - abs(2.0 * fr - 1.0));
    }
    st = clamp(st * 2.0, 0.0, 1.7);
    float edge = smoothstep(rin * 0.95, rin * 1.2, r) * pow(clamp((rout - r) / (rout * 0.55), 0.0, 1.0), 1.3);
    float sr = clamp((r - rin) / (rout - rin), 0.0, 1.0);
    vec3 hue = mix(vec3(1.0, 0.92, 0.78), vec3(1.0, 0.42, 0.10), pow(sr, 0.45));
    hue = mix(hue, vec3(0.75, 0.85, 1.0), clamp((g - 1.05) * 1.5, 0.0, 0.55));       // Doppler : côté qui approche
    hue = mix(hue, vec3(0.9, 0.18, 0.05), clamp((0.95 - g) * 1.6, 0.0, 0.7));         // côté qui s'éloigne
    vec3 col = hue * I * (0.15 + st * 1.5) * edge * 1.9;
    float cover = clamp(I * (0.2 + st * 0.9) * edge * 1.4, 0.0, 1.0);

    // le flux de l'étoile : part de l'étoile, s'enroule vers le bord du disque en s'élargissant
    float r0 = star.x - star.z * 0.8;
    float s = mod(star.y - phi + 12.566370, 6.2831853) / 4.0;
    if (s <= 1.0) {
        float rc = r0 * pow(rout * 0.85 / r0, pow(s, 0.7));
        float width = 0.9 + 3.2 * pow(s, 1.3);
        float d = (r - rc) / width;
        float fl = s * 4.0 - t * 0.5;
        float fil = fbm(vec2(fl, d * 0.9 + 3.0)) * 0.9 + fbm(vec2(fl * 2.7 + 0.4, d * 2.2)) * 0.7 - 0.6;
        fil = clamp(fil * 2.6, 0.0, 1.6);
        float prof = exp(-d * d * 1.2) * (0.12 + fil);
        float fade = smoothstep(0.0, 0.05, s) * pow(clamp((1.0 - s) / 0.35, 0.0, 1.0), 0.9);
        float sh = prof * fade * pow(clamp(g, 0.6, 1.6), 1.5) * 1.1;
        vec3 scol = mix(vec3(1.0, 0.78, 0.55), vec3(1.0, 0.45, 0.15), s);
        col += (1.0 - cover) * scol * sh;
        cover += (1.0 - cover) * clamp(sh * 0.55, 0.0, 1.0);
        float spot = exp(-pow((s - 0.93) / 0.05, 2.0)) * exp(-d * d * 0.6) * 1.2;   // impact au bord du disque
        col += (1.0 - cover) * vec3(1.0, 0.85, 0.6) * spot * (0.85 + 0.3 * sin(t * 3.1));
        cover += (1.0 - cover) * clamp(spot * 0.6, 0.0, 1.0);
    }
    return vec4(col, cover);
}

// l'étoile, vue à travers la lentille : on prolonge le rayon jusqu'à la profondeur de l'étoile
vec4 starLight(vec3 pos, vec3 v, float t) {
    float tl = geo.x;
    vec2 sp = star.x * vec2(cos(star.y), sin(star.y));
    vec3 S = vec3(sp.x, sp.y * sin(tl), -sp.y * cos(tl));             // plan du disque -> repère du trou
    if (v.z > -0.05) return vec4(0.0);
    vec2 P = pos.xy + v.xy * ((S.z - pos.z) / v.z);
    vec2 toHole = normalize(-S.xy), perp = vec2(-toHole.y, toHole.x);
    vec2 dl = P - S.xy;
    float along = dot(dl, toHole);
    float k = along > 0.0 ? star.w : 1.0;                              // goutte : étirée du côté du trou
    vec2 local = vec2(along / k, dot(dl, perp)) / star.z;
    float q2 = dot(local, local);
    if (q2 > 9.0) return vec4(0.0);
    float rr = sqrt(q2);
    float body = smoothstep(1.0, 0.9, rr);
    vec3 nrm = vec3(local, sqrt(max(1.0 - q2, 0.0)));
    float boil = fbm3(vec3(local * 2.6, t * 0.22)) * 0.75 + fbm3(vec3(local * 8.0, t * 0.5) + 3.0) * 0.45;
    float limb = pow(max(nrm.z, 0.0), 0.5);
    vec3 surf = mix(vec3(1.0, 0.45, 0.15), vec3(1.0, 0.97, 0.9), smoothstep(0.35, 0.95, boil));
    vec3 col = surf * (0.25 + 0.9 * limb) * (0.55 + boil) * body * 1.15;
    float corona = exp(-max(rr - 0.9, 0.0) * 2.4) * (1.0 - body);
    float flare = corona * (0.6 + 0.6 * fbm3(vec3(local * 2.0, t * 0.3) + 8.0));
    col += vec3(1.0, 0.55, 0.25) * flare * 0.55;
    return vec4(col, clamp(body + flare * 0.25, 0.0, 1.0));
}

vec3 scene(float t) {
    vec4 A = texture(bakeA, uv);
    ivec2 ts = textureSize(bakeB, 0);
    ivec2 tx = ivec2(min(uv * vec2(ts), vec2(ts) - 1.0));
    vec4 B = texelFetch(bakeB, tx, 0), C = texelFetch(bakeC, tx, 0), V = texelFetch(bakeD, tx, 0);
    vec3 pos = texelFetch(bakeA, tx, 0).xyz, v = V.xyz;
    // la colonne des rayons qui passent par l'axe de spin (L ~ 0) part en pointillés : loin du trou, on prend
    // le rayon du pixel voisin
    vec2 d0 = (uv - hole.xy) * size / hole.z;
    float bx = d0.x * cos(hole.w) + d0.y * sin(hole.w);                 // abscisse dans le repère du trou (roulis défait)
    if (length(d0) > 4.0 && abs(bx) * hole.z < 5.0) {
        ivec2 nx = tx + ivec2(bx < 0.0 ? -7 : 7, 0);
        pos = texelFetch(bakeA, nx, 0).xyz; v = texelFetch(bakeD, nx, 0).xyz;
    }
    vec3 rgb = vec3(0.0);
    if (A.w < 0.5) {
        vec2 src = v.z < -0.05 ? pos.xy + v.xy * ((-dsrc - pos.z) / v.z) : pos.xy + normalize(v.xy + 1e-6) * 300.0;
        // là où deux pixels voisins voient des coins du ciel très éloignés (anneau de photons), on adoucit
        float spread = length(fwidth(src)) / (48.0 / size.x);
        vec3 c = sky(src, t);
        rgb = mix(c, vec3(0.012, 0.008, 0.016), smoothstep(3.0, 18.0, spread));
        rgb *= smoothstep(0.0, 0.25, 1.0 - A.w);
    }
    vec4 sl = starLight(pos, v, t);
    if (A.w < 0.5) rgb = rgb * (1.0 - sl.a) + sl.rgb;
    vec4 back = diskLight(C, t);
    rgb = rgb * (1.0 - back.a) + back.rgb;
    vec4 front = diskLight(B, t);
    rgb = rgb * (1.0 - front.a) + front.rgb;
    return rgb;
}

void main() {
    // boucle : de 0 à F, fondu de l'état t + T vers t ; out(T) = out(0)
    float a = 1.0 - smoothstep(0.0, fadeF, t0);
    vec3 c = scene(t0);
    if (a > 0.0) c = mix(c, scene(t0 + loopT), a);
    frag = vec4(c, 1.0);                                              // HDR, le bloom et le tonemap suivent
}
"""


BLUR = """
#version 410
in vec2 uv;
out vec4 frag;
uniform sampler2D src;
uniform vec2 dir;          // pas en uv
uniform float bright;      // 1 : ne garder que ce qui dépasse 1 (première passe)
void main() {
    float w[7] = float[](0.1964825501511404, 0.2969069646728344, 0.09447039785044732, 0.010381362401148057, 0.0, 0.0, 0.0);
    vec3 c = vec3(0.0);
    for (int i = -3; i <= 3; i++) {
        vec3 s = texture(src, uv + dir * float(i) * 1.5).rgb;
        if (bright > 0.5) s = max(s - 0.8, 0.0);
        c += s * w[abs(i)];
    }
    frag = vec4(c * 1.35, 1.0);
}
"""

FINAL = """
#version 410
in vec2 uv;
out vec4 frag;
uniform sampler2D hdr, bloomA, bloomB;
uniform vec2 size;
uniform float t0;
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
vec3 tonemap(vec3 c) {
    c = c * (2.51 * c + 0.03) / (c * (2.43 * c + 0.59) + 0.14);   // ACES approché
    return pow(clamp(c, 0.0, 1.0), vec3(1.0 / 2.2));
}
void main() {
    vec3 c = texture(hdr, uv).rgb + texture(bloomA, uv).rgb * 0.55 + texture(bloomB, uv).rgb * 0.45;
    vec2 vg = uv - 0.5;
    c *= (1.0 - 0.45 * dot(vg, vg)) * 1.1;
    vec3 o = tonemap(c);
    o += (hash(uv * size + fract(t0) * 91.0) - 0.5) / 255.0;          // grain : pas de bandes à l'encodage
    frag = vec4(o, 1.0);
}
"""

PARAMS = dict(
    hole=(0.56, 0.56, 0.0, 0.18),   # centre (fractions, y vers le haut), rs (fixé selon la largeur), roulis
    geo=(0.17, 3.0, 15.0, 0.9),     # inclinaison (presque de profil), rin, rout, spin
    star=(24.0, 2.7, 1.9, 2.2),     # r, phi, rayon, étirement vers le trou
    dsrc=30.0,                      # profondeur du ciel (rs)
)


def make(w, h):
    ctx = moderngl.create_standalone_context(require=410)
    quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4"))
    rs = w / 48.0                      # ~40 px de rs en 1920 : ombre ~ 210 px de large
    hole = (PARAMS["hole"][0], PARAMS["hole"][1], rs, PARAMS["hole"][3])

    bake = ctx.program(vertex_shader=VERT, fragment_shader=BAKE)
    texs = [ctx.texture((w, h), 4, dtype="f4") for _ in range(4)]
    for t in texs:
        t.filter = (moderngl.LINEAR, moderngl.LINEAR)
    fbo = ctx.framebuffer(color_attachments=texs)
    bake["size"].value = (w, h)
    bake["hole"].value = hole
    bake["geo"].value = PARAMS["geo"]
    vao = ctx.vertex_array(bake, [(quad, "2f", "pos")])
    fbo.use()
    fbo.clear()
    bands = max(8, h // 24)
    for i in range(bands):                       # par bandes : le GPU ne bloque jamais longtemps
        bake["band"].value = (i / bands, (i + 1) / bands)
        vao.render(moderngl.TRIANGLE_STRIP)
        ctx.finish()
        print(f"\rbake {i + 1}/{bands}", end="", file=sys.stderr)
    print(file=sys.stderr)

    prog = ctx.program(vertex_shader=VERT, fragment_shader=FRAME)
    for i, name in enumerate(["bakeA", "bakeB", "bakeC", "bakeD"]):
        texs[i].use(i)
        prog[name].value = i
    prog["size"].value = (w, h)
    prog["hole"].value = hole
    prog["geo"].value = PARAMS["geo"]
    prog["star"].value = PARAMS["star"]
    prog["dsrc"].value = PARAMS["dsrc"]
    hdr = ctx.texture((w, h), 4, dtype="f2")
    hdr.filter = (moderngl.LINEAR, moderngl.LINEAR)
    hfbo = ctx.framebuffer(color_attachments=[hdr])
    fvao = ctx.vertex_array(prog, [(quad, "2f", "pos")])

    # bloom : deux niveaux (1/4 et 1/16), flou séparable
    blur = ctx.program(vertex_shader=VERT, fragment_shader=BLUR)
    bvao = ctx.vertex_array(blur, [(quad, "2f", "pos")])
    def level(div):
        a_ = ctx.texture((w // div, h // div), 4, dtype="f2"); b_ = ctx.texture((w // div, h // div), 4, dtype="f2")
        for t_ in (a_, b_):
            t_.filter = (moderngl.LINEAR, moderngl.LINEAR); t_.repeat_x = False; t_.repeat_y = False
        return a_, b_, ctx.framebuffer(color_attachments=[a_]), ctx.framebuffer(color_attachments=[b_]), div
    levels = [level(4), level(16)]

    fin = ctx.program(vertex_shader=VERT, fragment_shader=FINAL)
    fin["size"].value = (w, h)
    out = ctx.texture((w, h), 3)
    ofbo = ctx.framebuffer(color_attachments=[out])
    finvao = ctx.vertex_array(fin, [(quad, "2f", "pos")])

    def frame(t, loop_t, fade):
        prog["t0"].value = t
        prog["loopT"].value = loop_t
        prog["fadeF"].value = fade
        for i, t_ in enumerate(texs):            # le bloom réutilise les unités 0..2 : on rebranche le bake
            t_.use(i)
        hfbo.use()
        fvao.render(moderngl.TRIANGLE_STRIP)
        src, first = hdr, True
        for a_, b_, fa, fb, div in levels:
            lw, lh = w // div, h // div
            fa.use(); src.use(0); blur["src"].value = 0
            blur["dir"].value = (1.0 / lw, 0.0); blur["bright"].value = 1.0 if first else 0.0
            bvao.render(moderngl.TRIANGLE_STRIP)
            fb.use(); a_.use(0)
            blur["dir"].value = (0.0, 1.0 / lh); blur["bright"].value = 0.0
            bvao.render(moderngl.TRIANGLE_STRIP)
            src, first = b_, False
        ofbo.use()
        hdr.use(0); levels[0][1].use(1); levels[1][1].use(2)
        fin["hdr"].value = 0; fin["bloomA"].value = 1; fin["bloomB"].value = 2; fin["t0"].value = t
        finvao.render(moderngl.TRIANGLE_STRIP)
        data = ofbo.read(components=3)
        return np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)[::-1]
    return frame


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["still", "video"])
    ap.add_argument("out")
    ap.add_argument("--w", type=int, default=960)
    ap.add_argument("--h", type=int, default=540)
    ap.add_argument("--t", type=float, default=10.0)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--fade", type=float, default=4.0)
    ap.add_argument("--crf", type=int, default=16)
    a = ap.parse_args()
    frame = make(a.w, a.h)
    if a.mode == "still":
        from PIL import Image
        Image.fromarray(frame(a.t, a.seconds, a.fade)).save(a.out)
        return
    n = int(a.seconds * a.fps)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{a.w}x{a.h}",
        "-r", str(a.fps), "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", str(a.crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(frame(i / a.fps, a.seconds, a.fade).tobytes())
        if i % 30 == 0:
            print(f"\rframe {i}/{n}", end="", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    print(file=sys.stderr)


if __name__ == "__main__":
    main()
