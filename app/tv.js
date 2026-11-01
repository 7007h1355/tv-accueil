// Tout ce qui parle à la TV. Le reste de l'appli ne touche ni WebSocket ni API TV.

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
  remote.onmessage = (m) => report('remote ' + m.data.slice(0, 160));
  return remote;
}

async function launchModule(fullName) {
  const list = await modules;
  const mdl = list.find((m) => m.fullName === fullName);
  if (!mdl) throw new Error('module absent');
  tb.send(JSON.stringify({ type: 5, payload: mdl }));
  if (!mdl.evaluateScriptOnDocumentStart) location.href = mdl.appPath;
}

function sendKey(key) {
  const ws = remoteSocket();
  const msg = JSON.stringify({
    method: 'ms.remote.control',
    params: { Cmd: 'Click', DataOfCmd: key, Option: 'false', TypeOfRemote: 'SendRemoteKey' },
  });
  return new Promise((resolve, reject) => {
    const send = () => { ws.send(msg); report('key ' + key); resolve(); };
    if (ws.readyState === 1) return send();
    ws.addEventListener('open', send, { once: true });
    ws.addEventListener('error', () => reject(new Error('télécommande refusée')), { once: true });
  });
}

function run(action) {
  if (action.kind === 'module') return launchModule(action.name);
  if (action.kind === 'key') return sendKey(action.key);
}
