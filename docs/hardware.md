# Matériel

## Vue d'ensemble

```
 [alimentation 12 V] --> [module Pololu] --+--> Carte NG-RIE <-- pesons
                          ^ ON     ^ OFF   |        | A/B RS-485
   capteur de vibration --+        |       |   [module MAX485]
   (coup de pied)                  |       |        | RO / DI / DE-RE
                                   +-- A4 -+--> Arduino UNO R3 (VIN) --> afficheur TM1637
```

Toutes les masses (GND) sont communes : alimentation, carte, Arduino, module RS-485.

Dans un premier temps, l'alimentation 12 V est le bloc secteur. Le passage sur piles (4 AA + élévateur 12 V) se
fera ensuite : le module Pololu se placera alors côté piles, avant l'élévateur (voir plus bas).

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

Choix fait pour réutiliser le stock. À acheter : le module MAX485, l'afficheur TM1637 et le module Pololu (voir
[liste de courses](shopping-list.md)).

| Élément | Choix | Remarques |
|---|---|---|
| Microcontrôleur | **Arduino UNO R3** (en stock) | Démarre en moins d'1 s. 1 seul port série matériel (D0/D1), gardé pour l'USB : le RS-485 passe par un port série logiciel |
| Interface RS-485 | **module MAX485** « TTL vers RS485 » (5 V), **à acheter** | Le câble FTDI ne peut pas se brancher sur un Arduino |
| Afficheur | **module TM1637** 4 chiffres, **à acheter**, avec un point décimal à chaque chiffre | 2 fils de données ; le module gère seul l'allumage des chiffres |
| Historique des pesées | EEPROM interne de 1 Ko | environ 490 pesées, récupérées par USB |

### Brochage proposé

| Broche UNO | Rôle |
|---|---|
| D0, D1 | USB (téléversement, récupération de l'historique) : ne rien brancher |
| D8 (RX), D9 (TX) | RS-485 : D8 ← RO du MAX485, D9 → DI. Bibliothèque AltSoftSerial, plus fiable que SoftwareSerial (elle impose D8/D9 et rend D10 inutilisable en PWM) |
| D7 | DE et RE du MAX485, reliés ensemble (1 = émission, 0 = réception) |
| D2, D3 | CLK et DIO du TM1637 |
| A4 | entrée OFF du module Pololu (une impulsion éteint tout) |
| autres | libres |

### Alimentation de l'UNO

La broche VIN de l'UNO accepte de 7 à 12 V : elle se branche directement sur le 12 V de la carte. Le régulateur de
l'UNO chauffe un peu, ce qui est sans conséquence vu que la balance ne reste allumée que quelques dizaines de
secondes. Le TM1637 et le MAX485 sont alimentés par le 5 V de l'UNO.

## Réveil par coup de pied et arrêt automatique

Principe : le **module Pololu Mini Pushbutton Power Switch** (version LV) coupe tout quand la balance dort, en ne
consommant presque rien. Un coup de pied fait vibrer un capteur, qui envoie une impulsion sur l'entrée ON du module :
tout s'allume. Après 30 s à `0`, l'Arduino enregistre le zéro en EEPROM puis envoie une impulsion sur l'entrée OFF
par la broche A4 : tout s'éteint.

Délai entre le coup de pied et le `0` : environ **2 à 3 s**, le temps de démarrage mesuré de la carte Mettler
(l'Arduino, lui, démarre en moins d'1 s).

Points d'attention :

- **Le capteur va sur l'entrée ON**, pas sur le bouton : le bouton est une bascule marche/arrêt, qu'un coup en
  montant sur la balance suffirait à éteindre. Vérifier le câblage exact de ON et OFF sur la fiche du module.
- Le module accepte jusqu'à 20 V : il convient au bloc 12 V comme aux piles.

### Capteur de vibration

- **SW-520D (en stock)** : c'est un capteur d'inclinaison. Monté légèrement penché, juste à la limite où la bille
  bascule, un choc la fait sauter et ferme brièvement le contact. À essayer en premier. Il doit être **ouvert au
  repos**, sinon l'entrée ON resterait active.
- **SW-18010P** (à ressort, moins de 1 €) : plus sensible, si le SW-520D ne suffit pas.
- Pas de capteur à mercure : toxique, et interdit à la vente.

## Passage sur piles (plus tard)

- **4 piles AA** (6 V neuves, environ 4 V en fin de vie) et un **élévateur de tension** réglé sur 12 V (module
  MT3608, à acheter). **Régler sa sortie sur 12 V au multimètre avant de brancher quoi que ce soit.**
- Le module Pololu se place **côté piles, avant l'élévateur** : un élévateur consomme un peu même sans charge, ce
  qui viderait les piles en quelques mois s'il restait branché en permanence. Le module fonctionne dès 2,2 V.

À vérifier :

- **La consommation réelle** : multimètre en série sur le 12 V, balance allumée. Elle fixe l'autonomie : avec
  environ 1,5 W et 30 s par pesée, compter de l'ordre de 1 000 pesées par jeu de piles.
- **Le bruit de mesure** : un élévateur découpe le courant. Comparer `ng_rie_probe.py watch` sur le bloc secteur
  et sur l'élévateur.
- **Le temps de démarrage de la carte Mettler** sur piles : 2 à 3 s mesurés sur le bloc secteur.
