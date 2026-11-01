// icon : SVG 24x24 en traits, colorée par currentColor ; glow : teinte du halo au focus
const ICON_PLAY = '<svg viewBox="0 0 24 24"><rect x="2.5" y="5" width="19" height="14" rx="4"/><path d="M10 9.2v5.6l4.8-2.8z" fill="currentColor" stroke="none"/></svg>';
const ICON_HDMI = '<svg viewBox="0 0 24 24"><path d="M3 8h18v4.5l-2.5 3.5h-13L3 12.5z"/><path d="M7 11h10"/></svg>';

const TILES = [
  { id: 'youtube', label: 'YouTube', sub: 'TizenTube', icon: ICON_PLAY, glow: '255,72,96', action: { kind: 'module', name: 'npm/@foxreis/tizentube' } },
  { id: 'hdmi1', label: 'HDMI 1', sub: 'Entrée', icon: ICON_HDMI, glow: '96,190,255', action: { kind: 'key', key: 'KEY_HDMI1' } },
  { id: 'hdmi2', label: 'HDMI 2', sub: 'Entrée', icon: ICON_HDMI, glow: '96,190,255', action: { kind: 'key', key: 'KEY_HDMI2' } },
  { id: 'hdmi3', label: 'HDMI 3', sub: 'Entrée', icon: ICON_HDMI, glow: '96,190,255', action: { kind: 'key', key: 'KEY_HDMI3' } },
  { id: 'hdmi4', label: 'HDMI 4', sub: 'Entrée', icon: ICON_HDMI, glow: '96,190,255', action: { kind: 'key', key: 'KEY_HDMI4' } },
];
