# Capacités réelles de la page module (mesurées 2026-11-01, app/diag.html)

TV QE85Q80BATXXC, TizenBrew NextGen 2.0.5.

- UA : Tizen 6.5, Chromium 108.0.5359.1. Viewport 1920x1080, dpr 1.
- `tizen` et `webapis` : **absents** (page servie par http://127.0.0.1:8081). Pas de
  `tizen.tvinputdevice.registerKey` → seules les touches non enregistrées arrivent
  (flèches, OK, retour).
- WebGL 1 : oui (« WebKit WebGL »).
- Vidéo : `canPlayType('video/mp4; codecs="hvc1"')` = "" ; H.264 `avc1.640033` = "probably".
  → fond en H.264.
- Service TizenBrew `ws://localhost:8081` : joignable. `GetModules` renvoie
  `npm/@foxreis/tizentube` (mods, `https://youtube.com/tv?additionalDataUrl=…`) et
  `gh/7007h1355/tv-launcher` (app).
- REST TV `http://127.0.0.1:8001/api/v2/` : joignable depuis la page.
- WebSocket remote `ws://127.0.0.1:8001/api/v2/channels/samsung.remote.control` : s'ouvre
  puis `ms.channel.timeOut` → la TV demande une autorisation pour « Accueil ».
- Retour d'information : la page peut POSTer vers le Mac (`http://192.168.1.176:8765/log`).

Décisions : HDMI par `KEY_HDMI1..4` sur le remote 8001 une fois « Accueil » autorisé ;
vidéo H.264.
