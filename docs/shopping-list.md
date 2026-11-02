# Liste de courses

Liste établie à partir des choix décrits dans [hardware.md](hardware.md). Les prix sont des ordres de grandeur.

## Déjà en main

| Élément | Usage |
|---|---|
| Carte Mettler Toledo NG-RIE | lecture des pesons |
| 2 pesons Mettler Toledo 50 kg | |
| Câble FTDI USB-RS485-WE-5000-BT | banc de test sur PC (pas dans le montage final) |
| Bloc secteur 12 V | banc de test sur PC |
| Capteur à bille SW-520D | premier essai du réveil par coup de pied |
| Afficheur 5461AS | non utilisé (remplacé par un TM1637) |

## À acheter : électronique

| Élément | Qté | Prix | Points d'attention |
|---|---|---|---|
| **Arduino Nano Every** | 1 | ~12 € | Seulement si tu n'as pas déjà une carte Arduino utilisable. Une Uno marcherait aussi, avec un port série logiciel. |
| Câble micro-USB **de données** | 1 | | Pour téléverser le programme dans la Nano Every. Un câble « charge seule » ne marche pas. |
| **Module MAX485** « TTL vers RS485 », 5 V | 2 | ~2 € pièce | Le 2ᵉ en secours, ils sont souvent vendus par lots. |
| **Module TM1637** 4 chiffres | 2 | ~2 € pièce | **Prendre un modèle avec un point décimal à chaque chiffre.** Beaucoup de modules TM1637 sont des versions « horloge » avec seulement les deux-points `:` au milieu : ils ne peuvent pas afficher `67.4`. Vérifier sur la photo. |
| **Élévateur de tension MT3608** (réglable) | 2 | ~2 € pièce | **Régler la sortie sur 12 V au multimètre avant de brancher la carte** : le réglage d'usine peut être bien plus haut. |
| **Boîtier pour 4 piles AA** avec fils | 1 | ~2 € | Un modèle avec interrupteur est pratique pour tout couper pendant le montage. |
| 4 piles AA | 4 | | Alcalines, ou NiMH rechargeables (avec un chargeur si tu n'en as pas). |
| **Interrupteur électronique à verrouillage**, par ex. Pololu Mini Pushbutton Power Switch LV | 1 | ~6 € | **Vérifier sur la fiche qu'il a une entrée « marche seulement » (ON)** en plus du bouton marche/arrêt, et une entrée « arrêt » (OFF) pilotable par l'Arduino. Tension max 20 V : on le place côté piles (6 V). |
| **Capteur de vibration à ressort** SW-18010P | 3 | <1 € pièce | Pour le réveil par coup de pied, si le SW-520D ne suffit pas. |
| Câbles Dupont mâle/femelle, plaque à essais | | ~5 € | Pour les essais. |
| Plaque à pastilles, borniers à vis, gaine thermorétractable | | ~5 € | Pour le montage définitif. |
| Connecteurs adaptés à la carte Mettler (12 V, RS-485 A/B, GND) | | | **À identifier** : regarder le type de connecteur sur la carte, ou garder les fils actuels avec des borniers. |

## À acheter : mécanique

| Élément | Qté | Points d'attention |
|---|---|---|
| **Butées de surcharge** : vis (M6 ou M8), écrous et contre-écrous | 2 jeux | Une sous chaque peson, réglée avec un petit jeu (de l'ordre de 0,5 mm, selon la flèche du peson à pleine charge). C'est la seule vraie protection des pesons. |
| Petit boîtier plastique pour l'électronique | 1 | Avec une découpe pour l'afficheur. |
| Masse étalon de 1 kg (classe M1) | 1 | Facultatif, si la masse actuelle n'a pas été vérifiée sur une balance de cuisine. |

## Outillage

| Élément | Pourquoi |
|---|---|
| **Multimètre** | régler l'élévateur sur 12 V ; mesurer la consommation de la carte |
| Fer à souder et étain | modules, plaque à pastilles |
| Tournevis de précision | potentiomètre de l'élévateur, borniers |
