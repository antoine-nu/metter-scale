# Matériel

## Vue d'ensemble

```
 [4 piles AA] --> [interrupteur à verrouillage] --> [élévateur 12 V] --+--> Carte NG-RIE <-- pesons
                    ^ ON (réveil)    ^ OFF                             |        | A/B RS-485
   capteur de vibration              |                                 |   [module MAX485]
                                     +---------- broche Arduino        |        | TX / RX / DE-RE
                                                                       +--> Arduino (VIN) --> TM1637
```

Toutes les masses (GND) sont communes : piles, carte, Arduino, module RS-485.

## Pesons et mécanique

- 2 pesons Mettler Toledo de **50 kg** chacun (100 kg au total), un à gauche, un à droite, centrés sur la planche.
- Des semelles centrent la charge entre l'avant et l'arrière.
- La planche ne repose **que** sur les pesons : tout autre appui fausse la mesure.

**Risque de surcharge.** Une personne de 100 kg centrée met 50 kg par peson, soit la charge nominale. En se
décalant à gauche ou à droite, ou au moment de monter (choc d'environ 1,3 à 1,5 fois le poids), un peson peut
dépasser 70 kg. La surcharge admissible est souvent de 150 % (à vérifier sur la fiche du peson).

- À faire : une **butée mécanique** sous chaque peson (vis de réglage avec un petit jeu). C'est la seule vraie
  protection.
- Logiciel : l'afficheur montre `  OL` dès qu'un peson dépasse 60 kg. C'est un avertissement, pas une protection.

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

## Montage final

| Élément | Choix | Pourquoi |
|---|---|---|
| Microcontrôleur | Arduino **Nano Every** | 2ᵉ port série matériel (Serial1) qui laisse l'USB libre pour le débogage ; VIN accepte de 7 à 21 V |
| Interface RS-485 | module **MAX485** « TTL vers RS485 » (5 V), à acheter | standard, environ 2 €. DE et RE reliés ensemble sur une broche |
| Afficheur | module **TM1637** 4 chiffres, à acheter | 2 fils, environ 2 €. Le 5461AS disponible marcherait aussi, mais demande 12 broches, 8 résistances et un rafraîchissement permanent |

## Alimentation sur piles

- **4 piles AA** (6 V neuves, environ 4 V en fin de vie), alcalines ou NiMH rechargeables.
- Un **élévateur de tension** réglé sur 12 V (module MT3608, environ 2 €). Il accepte de 2 à 24 V en entrée.
- Ce 12 V alimente **à la fois la carte et l'Arduino** : la carte veut 12 V, et la broche VIN de la Nano Every
  accepte de 7 à 21 V. L'Arduino consomme quelques dizaines de mA, la carte probablement un peu plus : à mesurer.

À vérifier :

- **La consommation réelle** : multimètre en série sur le 12 V, balance allumée. Elle fixe l'autonomie : avec
  environ 1,5 W et 30 s par pesée, compter de l'ordre de 1 000 pesées par jeu de piles.
- **Le bruit de mesure** : un élévateur découpe le courant. Comparer `ng_rie_probe.py watch` sur le bloc secteur
  et sur l'élévateur.

## Réveil par coup de pied et arrêt automatique

- Un **interrupteur électronique à verrouillage** entre les piles et l'élévateur, par exemple un *Pololu Mini
  Pushbutton Power Switch* (version LV, jusqu'à 20 V), qui ne consomme presque rien quand il est éteint.
- Un **capteur de vibration** fixé sous la planche déclenche la mise en marche. Un ressort (type SW-18010P) est le
  plus sensible.
- L'Arduino **coupe lui-même l'alimentation** par une broche après 30 s à `0`, après avoir enregistré le zéro en
  EEPROM.

Points d'attention :

- **Le capteur doit seulement allumer.** Sur ces modules, l'entrée « bouton » est souvent une bascule
  marche/arrêt : un coup en montant sur la balance l'éteindrait. Il faut brancher le capteur sur une entrée
  « marche seulement » (ON). Vérifier sur la fiche du modèle choisi avant l'achat.
- **Capteur à bille SW-520D (disponible)** : c'est un capteur d'inclinaison. Monté légèrement penché, juste à la
  limite où la bille bascule, un choc la fait sauter et ferme brièvement le contact, ce qui peut suffire comme
  détecteur de coup de pied. Il est moins sensible et moins fiable qu'un capteur à ressort, mais il permet
  d'essayer. Il doit être **ouvert au repos**, sinon l'entrée ON resterait active et empêcherait l'arrêt.
- Pas de capteur à mercure : toxique, et interdit à la vente.
