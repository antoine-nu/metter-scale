# Matériel

## Vue d'ensemble

```
 [alimentation 12 V] --> [verrou d'alimentation] --+--> Carte NG-RIE <-- pesons
                          ^ ON        ^ maintien   |        | A/B RS-485
   capteur de vibration --+           |            |   [module MAX485]
   (coup de pied)                     |            |        | RO / DI / DE-RE
                                      +---- A4 ----+--> Arduino UNO R3 (VIN) --> afficheur 5461AS
```

Toutes les masses (GND) sont communes : alimentation, carte, Arduino, module RS-485.

Dans un premier temps, l'alimentation 12 V est le bloc secteur. Le passage sur piles (4 AA + élévateur 12 V) se
fera ensuite : le verrou se placera alors côté piles, avant l'élévateur (voir plus bas).

## Pesons et mécanique

- 2 pesons Mettler Toledo de **50 kg** chacun (100 kg au total), un à gauche, un à droite, centrés sur la planche.
- Des semelles centrent la charge entre l'avant et l'arrière.
- La planche ne repose **que** sur les pesons : tout autre appui fausse la mesure.

**Risque de surcharge.** Une personne de 100 kg centrée met 50 kg par peson, soit la charge nominale. En se
décalant à gauche ou à droite, ou au moment de monter (choc d'environ 1,3 à 1,5 fois le poids), un peson peut
dépasser 70 kg. La surcharge admissible est souvent de 150 % (à vérifier sur la fiche du peson).

- À faire : une **butée mécanique** sous chaque peson (vis de réglage avec un petit jeu). C'est la seule vraie
  protection.
- Logiciel : l'afficheur montre `  OL` quand un peson dépasse 80 kg pendant plus d'1 s (une montée sur un pied ne le déclenche pas). C'est un
  avertissement, pas une protection.

## Carte Mettler Toledo NG-RIE

- Alimentation **12 V**.
- 6 voies (pads 0 à 5), en mode « pad » : chaque voie est configurée et calibrée séparément.
- Pesons branchés sur **voie 0 = peson droit** et **voie 1 = peson gauche**. Les voies 2 à 5 sont libres.
- Configuration d'origine : 1 g par division, capacité 20 kg par voie, calibrée pour d'autres pesons. Elle n'est
  pas modifiée : la correction se fait côté Arduino (voir [calibrage](calibration.md)).

## Banc PC : câble FTDI USB-RS485-WE-5000-BT

Sert au diagnostic et à la simulation sur PC. Il ne servira pas au montage final : un Arduino ne peut pas piloter
un périphérique USB.

| Fil | Rôle | Branchement |
|---|---|---|
| Orange | Data+ (A) | A de la carte |
| Jaune | Data− (B) | B de la carte |
| Noir | GND | masse de la carte |
| Rouge | sortie 5 V | ne pas brancher |
| Marron + vert | résistance de terminaison 120 Ω | inutile sur un câble court à 9600 bauds |

Couleurs à confirmer sur la fiche FTDI. Si la carte ne répond pas, inverser A et B : tous les fabricants ne
nomment pas ces bornes de la même façon.

## Montage final : Arduino UNO R3

Choix fait pour réutiliser le stock. Seul le module MAX485 est à acheter (voir [liste de courses](shopping-list.md)).

| Élément | Choix | Remarques |
|---|---|---|
| Microcontrôleur | **Arduino UNO R3** (en stock) | Démarre en moins d'1 s. 1 seul port série matériel (D0/D1), gardé pour l'USB : le RS-485 passe par un port série logiciel |
| Interface RS-485 | **module MAX485** « TTL vers RS485 » (5 V), **à acheter** | Le câble FTDI ne peut pas se brancher sur un Arduino |
| Afficheur | **5461AS** (en stock), 4 chiffres à cathode commune | 12 broches et 8 résistances ; l'Arduino allume les chiffres l'un après l'autre en permanence (bibliothèque SevSeg) |
| Historique des pesées | EEPROM interne de 1 Ko | environ 490 pesées, récupérées par USB |

### Brochage proposé

| Broche UNO | Rôle |
|---|---|
| D0, D1 | USB (téléversement, récupération de l'historique) : ne rien brancher |
| D8 (RX), D9 (TX) | RS-485 : D8 ← RO du MAX485, D9 → DI. Bibliothèque AltSoftSerial, plus fiable que SoftwareSerial (elle impose D8/D9 et rend D10 inutilisable en PWM) |
| D7 | DE et RE du MAX485, reliés ensemble (1 = émission, 0 = réception) |
| D2, D3, D4, D5, D6, D11, D12, D13 | segments a, b, c, d, e, f, g, point de l'afficheur, chacun **à travers une résistance de 1 kΩ** |
| A0, A1, A2, A3 | cathodes communes des chiffres 1 à 4 |
| A4 | maintien du verrou d'alimentation (1 = rester allumé, 0 = s'éteindre) |
| A5, D10 | libres |

Avec 1 kΩ, un segment consomme environ 3 mA, donc au plus 24 mA sur la broche d'un chiffre (`8.` allumé). C'est
dans les limites de l'UNO. Avec des résistances plus faibles, l'affichage serait plus lumineux, mais il faudrait
des transistors sur les chiffres. La LED de D13 clignotera avec le segment « point » : sans conséquence.

Le brochage exact de l'afficheur 5461AS (quelle patte correspond à quel segment) sera vérifié au multimètre ou avec
une pile et une résistance avant de souder.

### Alimentation de l'UNO

La broche VIN de l'UNO accepte de 7 à 12 V : elle se branche directement sur le 12 V de la carte. Le régulateur de
l'UNO chauffe un peu, ce qui est sans conséquence vu que la balance ne reste allumée que quelques dizaines de
secondes.

## Réveil par coup de pied et arrêt automatique

Principe : un **verrou d'alimentation** coupe tout quand la balance dort, sans aucune consommation. Un coup de pied
fait vibrer un capteur, qui allume le verrou. L'Arduino démarre et **maintient** le verrou par la broche A4 ; après
30 s à `0`, il enregistre le zéro en EEPROM puis relâche A4, et tout s'éteint.

Le capteur ne ferme son contact que quelques millisecondes : le verrou doit rester allumé assez longtemps (environ
1 s) pour que l'Arduino démarre et prenne le relais.

### Option A : verrou fait maison (composants de stock)

```
 +12 V (toujours présent)
   |                     |
   |                  100 kΩ
   |                     |
 capteur                 +-------------- grille du MOSFET canal P
   |                     |               (source sur +12 V, drain vers la carte et VIN de l'UNO)
 100 Ω               collecteur
   |                   [NPN]
   +--- 47 µF --- GND    |
   |                   base -------+
   +--- 47 kΩ -----------+         |
                                 10 kΩ
                       émetteur    |
                         |       diode 1N4148
                        GND        |
                                  A4 de l'UNO
```

- Au repos : la résistance de 100 kΩ tient la grille du MOSFET au +12 V, il est bloqué, rien n'est alimenté.
- Coup de pied : le capteur charge le condensateur de 47 µF en un instant. Celui-ci se décharge lentement
  (47 µF × 47 kΩ, environ 2 s) dans la base du transistor NPN, qui tire la grille vers la masse : le MOSFET
  conduit, tout s'allume.
- L'Arduino met A4 à 1 dès le démarrage : le transistor reste passant même quand le condensateur est vide.
- A4 à 0 : tout s'éteint.

Composants : un MOSFET **canal P** supportant 12 V et quelques centaines de mA (par exemple IRF9540, IRF4905), un
NPN courant (BC547, 2N2222), résistances de 100 Ω, 10 kΩ, 47 kΩ et 100 kΩ, un condensateur de 47 µF, une diode
(1N4148). Les valeurs seront ajustées pendant les essais.

### Option B : module tout fait

Un *Pololu Mini Pushbutton Power Switch* (version LV, jusqu'à 20 V, environ 6 €). Vérifier sur sa fiche qu'il a une
entrée « marche seulement » (ON) pour le capteur et une entrée « arrêt » (OFF) pour l'Arduino : son bouton est une
bascule marche/arrêt, qu'un coup en montant sur la balance suffirait à éteindre.

### Capteur de vibration

- **SW-520D (en stock)** : c'est un capteur d'inclinaison. Monté légèrement penché, juste à la limite où la bille
  bascule, un choc la fait sauter et ferme brièvement le contact. À essayer en premier. Il doit être **ouvert au
  repos**, sinon la balance ne s'éteindrait jamais.
- **SW-18010P** (à ressort, moins de 1 €) : plus sensible, si le SW-520D ne suffit pas.
- Pas de capteur à mercure : toxique, et interdit à la vente.

## Passage sur piles (plus tard)

- **4 piles AA** (6 V neuves, environ 4 V en fin de vie) et un **élévateur de tension** réglé sur 12 V (module
  MT3608, à acheter). **Régler sa sortie sur 12 V au multimètre avant de brancher quoi que ce soit.**
- Le verrou d'alimentation se place **côté piles, avant l'élévateur** : un élévateur consomme un peu même sans
  charge, ce qui viderait les piles en quelques mois s'il restait branché en permanence.
- Côté piles, la tension n'est plus que de 4 à 6 V : le MOSFET canal P du verrou fait maison doit alors être un
  modèle « logic level », qui conduit franchement avec seulement 4 V sur sa grille (par exemple AO3401 ou
  IRLML6402). Un IRF9540 ne conviendrait plus. Le module Pololu, lui, fonctionne dès 2,2 V.

À vérifier :

- **La consommation réelle** : multimètre en série sur le 12 V, balance allumée. Elle fixe l'autonomie : avec
  environ 1,5 W et 30 s par pesée, compter de l'ordre de 1 000 pesées par jeu de piles.
- **Le bruit de mesure** : un élévateur découpe le courant. Comparer `ng_rie_probe.py watch` sur le bloc secteur
  et sur l'élévateur.
- **Le temps de démarrage de la carte Mettler** : c'est lui qui fixera le délai entre le coup de pied et le `0`.
