# Pèse-personne Mettler Toledo + Arduino

Un pèse-personne rudimentaire construit avec une planche posée sur **2 pesons Mettler Toledo de 50 kg**, une
**carte Mettler Toledo NG-RIE** (« AutoShelf ») qui lit les pesons, et un **Arduino** qui interroge la carte en
RS-485 et affiche le poids sur un **afficheur 7 segments de 4 chiffres**.

## Cas d'usage

- **Se peser** : un coup de pied réveille la balance (prévu), qui fait sa tare et affiche `0`. On monte : le poids
  s'affiche au dixième de kg (`67.4`), en kg entiers à partir de 100 kg (`112`). Il se fige après environ 4 s et
  clignote 2 fois pour signaler que la mesure est terminée. La balance s'éteint seule après 30 s à `0`.
- **Calibrer** : sur la balance vide, 3 appuis brefs de la main sur le peson gauche. On règle la masse de calibrage
  en appuyant à droite (+) ou à gauche (−), puis la balance guide l'utilisateur pour poser cette masse à gauche
  puis à droite.

Détails : [comportement de l'afficheur](docs/display-behaviour.md) et [calibrage](docs/calibration.md).

## État du projet

| Étape | État |
|---|---|
| Lecture et compréhension du protocole de la carte | fait ([protocole](docs/protocol-ng-rie.md)) |
| Dialogue PC ↔ carte via câble USB/RS-485 | fait, validé sur la vraie carte |
| Logique de la balance simulée sur PC (tare, pesée, calibrage, affichage) | fait, en cours de validation sur la vraie carte |
| Choix du matériel : Arduino UNO R3, afficheur 5461AS, module MAX485 | fait ([matériel](docs/hardware.md), [liste de courses](docs/shopping-list.md)) |
| Historique des pesées (EEPROM de l'UNO, récupération par USB, graphe par personne sur PC) | à faire |
| Réveil par coup de pied (verrou d'alimentation + capteur de vibration) | à faire |
| Firmware Arduino | à faire |
| Mécanique (butées de surcharge, boîtier) | à faire |

## Contenu du dépôt

```
tools/
  ng_rie_probe.py         outil de diagnostic de la carte (lecture seule) : info, watch
  scale_logic.py          logique de la balance, sans entrée/sortie : c'est elle qui sera portée sur l'Arduino
  scale_firmware_sim.py   fait tourner scale_logic.py sur PC avec la vraie carte, dessine l'afficheur
tests/
  test_probe.py           tests hors ligne des trames et du décodage
  test_firmware.py        scénarios hors ligne de la machine à états (balance simulée)
docs/
  protocol-ng-rie.md      synthèse du protocole de la carte et écarts constatés avec la doc
  hardware.md             matériel, alimentation, câblage
  shopping-list.md        liste de courses
  calibration.md          principe et procédure de calibrage
  display-behaviour.md    spécification de l'afficheur et de la machine à états (référence pour l'Arduino)
  measurements/           relevés faits sur la vraie carte
```

## Démarrage rapide (PC + câble USB/RS-485)

```
pip install -r requirements.txt

python tools/ng_rie_probe.py COM7 info            # identité et configuration de la carte
python tools/ng_rie_probe.py COM7 watch --channels 6   # poids bruts de chaque voie, en continu
python tools/scale_firmware_sim.py COM7          # la balance telle qu'elle fonctionnera
python tools/scale_firmware_sim.py COM7 --plain  # idem, une ligne par changement d'affichage (à copier-coller)
```

Le simulateur dessine l'afficheur 7 segments à un endroit fixe du terminal, avec sous lui l'état interne et le
poids calculé. Les messages (EEPROM enregistrée, carte introuvable...) défilent au-dessus. Il faut un terminal qui
comprend les séquences ANSI (Windows Terminal, PowerShell, VS Code, tout terminal Linux ou macOS) ; sinon,
utiliser `--plain`. Après 30 s à `0`, la balance « s'éteint » et le programme s'arrête : le relancer revient à la
réveiller.

Le port est `COMx` sous Windows (Gestionnaire de périphériques) ou `/dev/ttyUSB0` sous Linux. Les deux outils
n'envoient **que des commandes de lecture** à la carte : ils ne modifient ni sa configuration ni son calibrage. Le
simulateur enregistre son calibrage dans `scale_eeprom.json` (équivalent de l'EEPROM de l'Arduino, ignoré par git).

## Tests

```
python tests/test_probe.py
python tests/test_firmware.py
```

Ils tournent sans matériel. `test_firmware.py` rejoue des scénarios (montée, balancement, calibrage, perte de
liaison, surcharge) sur une balance simulée qui reprend les décalages et les gains mesurés sur la vraie carte.

## Documentation constructeur

La spécification « NG-RIE AutoShelf Communication Protocol V0.09 » de Mettler Toledo n'est pas versionnée ici (dépôt
public, document constructeur). Sa synthèse est dans [docs/protocol-ng-rie.md](docs/protocol-ng-rie.md).
