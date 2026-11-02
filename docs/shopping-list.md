# Liste de courses

Choix : **réutiliser le stock** au maximum (voir [hardware.md](hardware.md)). Les prix sont des ordres de grandeur.

## Déjà en main

| Élément | Usage |
|---|---|
| Carte Mettler Toledo NG-RIE et 2 pesons de 50 kg | mesure |
| **Arduino UNO R3** (x2) | cerveau de la balance (le 2ᵉ en secours ou pour les essais) |
| Afficheur 5461AS | non utilisé (remplacé par un TM1637) |
| Capteur à bille **SW-520D** | réveil par coup de pied (premier essai) |
| Bloc secteur 12 V | alimentation de la balance, puis du banc de test |
| Câble FTDI USB-RS485-WE-5000-BT | banc de test sur PC (pas dans le montage final) |
| Raspberry Pi 3, 4, 5 | non utilisés : démarrage trop lent, carte SD fragile en cas de coupure |

## À vérifier dans le stock

| Élément | Qté | Pour |
|---|---|---|
| Câble USB A-B (« imprimante ») | 1 | téléverser le programme dans l'UNO, récupérer l'historique |
| Câbles Dupont, plaque à essais | | essais |
| Plaque à pastilles, borniers à vis, gaine thermorétractable | | montage définitif |
| Multimètre, fer à souder | | réglages, mesures, montage |

## À acheter

| Élément | Qté | Prix | Indispensable ? |
|---|---|---|---|
| **Module MAX485** « TTL vers RS485 », 5 V | 2 | ~2 € pièce | **Oui** : sans lui, l'Arduino ne peut pas parler à la carte. Le 2ᵉ en secours, ils sont souvent vendus par lots |
| **Module TM1637** 4 chiffres | 2 | ~2 € pièce | **Oui. Prendre un modèle avec un point décimal à chaque chiffre** : beaucoup de TM1637 sont des versions « horloge » avec seulement `:` au milieu, qui ne peuvent pas afficher `67.4`. Vérifier sur la photo |
| **Pololu Mini Pushbutton Power Switch LV** | 1 | ~6 € | **Oui**, pour le réveil par coup de pied. Vérifier qu'il a des entrées ON et OFF séparées |
| Capteur de vibration à ressort SW-18010P | 3 | <1 € pièce | Seulement si le SW-520D ne réveille pas la balance de façon fiable |
| Élévateur de tension MT3608 réglable | 2 | ~2 € pièce | Plus tard, pour le passage sur piles. Régler la sortie sur 12 V avant de brancher quoi que ce soit |
| Boîtier 4 piles AA avec fils, 4 piles | 1 | ~2 € | Plus tard, pour le passage sur piles |

## Mécanique

| Élément | Qté | Points d'attention |
|---|---|---|
| **Butées de surcharge** : vis (M6 ou M8), écrous et contre-écrous | 2 jeux | Une sous chaque peson, réglée avec un petit jeu (de l'ordre de 0,5 mm, selon la flèche du peson à pleine charge). C'est la seule vraie protection des pesons |
| Petit boîtier pour l'électronique | 1 | Avec une découpe pour l'afficheur |
| Masse étalon de 1 kg (classe M1) | 1 | Facultatif, si la masse actuelle n'a pas été vérifiée sur une balance de cuisine |
