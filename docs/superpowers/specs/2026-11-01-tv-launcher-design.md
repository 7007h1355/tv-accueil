# Panneau de démarrage TV (TizenBrew) — design

Date : 2026-11-01
TV : Samsung QE85Q80BATXXC (Q80BA 85", Tizen 6.5, 2022), IP 192.168.1.2, filaire.
TizenBrew NextGen 2.0.5 (`xvvl3S1bvH.TizenBrewStandalone`), mode dev Host PC = 127.0.0.1.

## But

Remplacer le Smart Hub au quotidien : en allumant la TV, l'écran affiche un fond
spatial « de malade » (trou noir qui aspire une étoile, nébuleuse, étoiles) et
quelques tuiles de raccourcis. Rien d'autre.

## Contenu

- **Fond** : hybride.
  - Vidéo pré-rendue en boucle parfaite (~60 s) : trou noir de Kerr (spin 0.9,
    lentille gravitationnelle, disque d'accrétion) qui déchiquette une étoile
    (filament sur orbites réelles), nébuleuse et champ d'étoiles derrière.
    Réutilise la chaîne du jeu idle-game (proto Kerr numpy, `tools/houdini/tidal_star.py`,
    Blender) mais en rendu offline plein cadre, sans contrainte temps réel.
  - Couche WebGL légère par-dessus : étoiles proches en parallaxe lente et
    poussière qui spirale vers le trou, pour casser la répétition de la boucle.
    Budget : doit tenir 60 fps sur la TV, sinon on baisse le nombre de particules.
- **Tuiles** (bas d'écran, discrètes) : TizenTube, HDMI 1, HDMI 2, HDMI 3, HDMI 4.
  On peut retirer les HDMI inutilisées après test.
- **Pas** d'horloge, de météo ni d'autre appli.

## Comportement

- Navigation flèches gauche/droite + OK. Focus visible (halo).
- Après 10 s sans touche, les tuiles s'effacent en fondu ; une touche les fait revenir
  (cette touche ne déclenche rien d'autre).
- TizenTube : `POST http://127.0.0.1:8001/api/v2/applications/<id TizenTube>` ou, si
  TizenTube n'est qu'un module TizenBrew, retour à TizenBrew avec ce module.
  À trancher au premier test (voir Risques).
- HDMI : méthode à valider sur la TV, dans l'ordre d'essai :
  1. `tizen.tvwindow` / changement de source si l'API est exposée à la page ;
  2. touche distante `KEY_HDMI1..4` via le WebSocket remote local (port 8001/8002) ;
  3. sinon, tuile unique « Sources » qui ouvre le menu source.

## Démarrage auto

- TizenBrew : module en **autolaunch**.
- TV : Réglages → Général → Fonctions Smart : « Exécution auto de Smart Hub » **off**,
  « Exécuter auto la dernière appli » **on**. On laisse la TV sur TizenBrew.
- Le Smart Hub peut encore flasher une fraction de seconde : accepté, pas
  contournable (pas de lanceur remplaçable sur Tizen).

## Architecture

- Repo GitHub public `7007h1355/tv-launcher` (publication à valider par le porteur
  au moment de la créer).
- Module TizenBrew `packageType: app`, ajouté dans TizenBrew par `gh/7007h1355/tv-launcher`
  (TizenBrew charge via jsdelivr).
- Fichiers :
  - `package.json` — métadonnées module (`appName`, `appPath: app/index.html`, `keys`).
  - `app/index.html` — structure.
  - `app/launcher.js` — tuiles, focus, mise en veille des tuiles, lancement.
  - `app/sky.js` — couche WebGL (particules), indépendante du reste.
  - `app/style.css`.
- Vidéo : trop lourde pour jsdelivr (limite par fichier) → servie par GitHub Pages
  du même repo (`https://7007h1355.github.io/tv-launcher/sky.mp4`).
  Encodage : HEVC 3840x2160 + secours H.264 1920x1080. Boucle sans couture
  (première et dernière image identiques).
- Rendu offline (sur le Mac, hors repo publié) : `render/` avec les scripts de rendu.

## Erreurs

- Vidéo indisponible (réseau) → la couche WebGL seule reste affichée sur fond noir, tuiles OK.
- WebGL indisponible → vidéo seule.
- Lancement d'appli refusé → message court sur la tuile, pas de plantage.

## Vérification

- Développement sur le Mac dans le navigateur (1920x1080), navigation clavier.
- Sur la TV : lancement réel de TizenTube et des HDMI, fps de la couche WebGL
  mesuré (compteur caché), démarrage à froid de la TV jusqu'au panneau.

## Risques

- Changement HDMI depuis une page web : non garanti, d'où le repli « Sources ».
- Lancer TizenTube depuis un autre module : TizenTube est un module TizenBrew, pas
  une appli installée → il faudra sûrement passer par TizenBrew (message WebSocket
  au service TizenBrew pour lancer un module). À vérifier dans le code TizenBrew.
- Temps de rendu de la vidéo 4K : plusieurs heures possibles ; on valide d'abord sur
  une version courte basse résolution.
