# Pèse-personne Mettler Toledo + Arduino

Un pèse-personne rudimentaire construit avec une planche posée sur **2 pesons Mettler Toledo de 50 kg**, une
**carte Mettler Toledo NG-RIE** (« AutoShelf ») qui lit les pesons, et un **Arduino** qui interroge la carte en
RS-485 et affiche le poids sur un **afficheur 7 segments de 4 chiffres**.

## Cas d'usage

- **Se peser** : on met sous tension, la balance fait sa tare automatiquement et affiche `0`. On monte : le poids
  s'affiche au dixième de kg (`67.4`), en kg entiers à partir de 100 kg (`112`). Il se fige après environ 2 s et
  clignote 2 fois pour signaler que la mesure est terminée.
- **Calibrer** : on met sous tension en étant debout sur la balance, on attend le `0`, puis on descend. La balance
  passe en mode calibrage et guide l'utilisateur pour poser une masse de 1 kg à gauche puis à droite.

Détails : [comportement de l'afficheur](docs/display-behaviour.md) et [calibrage](docs/calibration.md).

## État du projet

| Étape | État |
|---|---|
| Lecture et compréhension du protocole de la carte | fait ([protocole](docs/protocol-ng-rie.md)) |
| Dialogue PC ↔ carte via câble USB/RS-485 | fait, validé sur la vraie carte |
| Logique de la balance simulée sur PC (tare, pesée, calibrage, affichage) | fait, en cours de validation sur la vraie carte |
| Firmware Arduino | à faire |
| Mécanique (butées de surcharge, boîtier) | à faire |

## Contenu du dépôt

```
tools/
  ng_rie_probe.py         outil de diagnostic de la carte (lecture seule) : info, watch
  scale_firmware_sim.py   simulation sur PC du futur firmware Arduino, pilotée par la vraie carte
tests/
  test_probe.py           tests hors ligne des trames et du décodage
  test_firmware.py        scénarios hors ligne de la machine à états (balance simulée)
docs/
  protocol-ng-rie.md      synthèse du protocole de la carte et écarts constatés avec la doc
  hardware.md             matériel, alimentation, câblage
  calibration.md          principe et procédure de calibrage
  display-behaviour.md    spécification de l'afficheur et de la machine à états (référence pour l'Arduino)
  measurements/           relevés faits sur la vraie carte
```

## Démarrage rapide (PC + câble USB/RS-485)

```
pip install -r requirements.txt

python tools/ng_rie_probe.py COM7 info            # identité et configuration de la carte
python tools/ng_rie_probe.py COM7 watch --channels 6   # poids bruts de chaque voie, en continu
python tools/scale_firmware_sim.py COM7 --mass 1000    # la balance telle qu'elle fonctionnera
```

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
