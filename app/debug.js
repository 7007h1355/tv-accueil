// Envoie les messages au Mac de dev (serveur de logs) ; silencieux si absent.
const SINK = 'http://192.168.1.176:8765/log';

function report(msg) {
  try { fetch(SINK, { method: 'POST', mode: 'no-cors', body: String(msg) }).catch(() => {}); } catch (e) {}
}

addEventListener('error', (e) => report('error ' + e.message + ' @' + e.filename + ':' + e.lineno));
addEventListener('unhandledrejection', (e) => report('rejection ' + (e.reason && e.reason.message || e.reason)));
