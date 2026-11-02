# Matériel

## Vue d'ensemble

```
 [Bloc 12 V continu] --+--> Carte NG-RIE <-- peson gauche (voie 1), peson droit (voie 0)
                       |        | A/B RS-485
                       |   [module MAX485]
                       |        | TX / RX / DE-RE
                       +--> Arduino (VIN) ----> afficheur TM1637 4 chiffres (CLK, DIO)
                                  +-----------> EEPROM interne : gains de calibrage
```

Toutes les masses (GND) sont communes : carte, Arduino, module RS-485.

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

## Montage final (à acheter)

| Élément | Choix proposé | Pourquoi |
|---|---|---|
| Microcontrôleur | Arduino **Nano Every** | 2ᵉ port série matériel (Serial1) qui laisse l'USB libre pour le débogage ; VIN accepte jusqu'à 21 V |
| Interface RS-485 | module **MAX485** « TTL vers RS485 » (5 V) | standard, environ 2 €. DE et RE reliés ensemble sur une broche |
| Afficheur | module **TM1637** 4 chiffres | 2 fils, environ 2 €, sait afficher `CAL`, `PL L`, `donE`, `Err`, `OL` |
| Alimentation | le bloc 12 V de la carte | l'Arduino est alimenté par VIN. Vérifier que le bloc sort bien du **12 V continu** |

Consommation estimée : carte + Arduino + afficheur, moins de 200 mA. Un bloc de 1 A suffit.
