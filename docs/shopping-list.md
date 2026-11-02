# Liste de courses

Choix : **réutiliser le stock** au maximum (voir [hardware.md](hardware.md)). Les prix sont des ordres de grandeur.

## Déjà en main

| Élément | Usage |
|---|---|
| Carte Mettler Toledo NG-RIE et 2 pesons de 50 kg | mesure |
| **Arduino UNO R3** (x2) | cerveau de la balance (le 2ᵉ en secours ou pour les essais) |
| Afficheur **5461AS** 4 chiffres, cathode commune | affichage |
| Capteur à bille **SW-520D** | réveil par coup de pied (premier essai) |
| Bloc secteur 12 V | alimentation de la balance, puis du banc de test |
| Câble FTDI USB-RS485-WE-5000-BT | banc de test sur PC (pas dans le montage final) |
| Raspberry Pi 3, 4, 5 | non utilisés : démarrage trop lent, carte SD fragile en cas de coupure |

## À vérifier dans le stock

| Élément | Qté | Pour |
|---|---|---|
| Résistances de 1 kΩ | 8 | segments de l'afficheur |
| Câble USB A-B (« imprimante ») | 1 | téléverser le programme dans l'UNO, récupérer l'historique |
| Câbles Dupont, plaque à essais | | essais |
| MOSFET canal P (IRF9540, IRF4905...), NPN (BC547, 2N2222), diode 1N4148, condensateur 47 µF, résistances 100 Ω, 10 kΩ, 47 kΩ, 100 kΩ | 1 de chaque | verrou d'alimentation fait maison (option A). S'il manque des pièces, voir l'option B ci-dessous |
| Plaque à pastilles, borniers à vis, gaine thermorétractable | | montage définitif |
| Multimètre, fer à souder | | brochage de l'afficheur, réglages, mesures |

## À acheter

| Élément | Qté | Prix | Indispensable ? |
|---|---|---|---|
| **Module MAX485** « TTL vers RS485 », 5 V | 2 | ~2 € pièce | **Oui** : sans lui, l'Arduino ne peut pas parler à la carte. Le 2ᵉ en secours, ils sont souvent vendus par lots |
| Pololu Mini Pushbutton Power Switch LV | 1 | ~6 € | Seulement si le verrou fait maison n'est pas possible avec le stock. Vérifier qu'il a des entrées ON et OFF séparées |
| Capteur de vibration à ressort SW-18010P | 3 | <1 € pièce | Seulement si le SW-520D ne réveille pas la balance de façon fiable |
| Élévateur de tension MT3608 réglable | 2 | ~2 € pièce | Plus tard, pour le passage sur piles. Régler la sortie sur 12 V avant de brancher quoi que ce soit |
| Boîtier 4 piles AA avec fils, 4 piles | 1 | ~2 € | Plus tard, pour le passage sur piles |
| MOSFET canal P « logic level » (AO3401, IRLML6402) | 2 | <1 € | Plus tard, pour le verrou fait maison côté piles |

## Mécanique

| Élément | Qté | Points d'attention |
|---|---|---|
| **Butées de surcharge** : vis (M6 ou M8), écrous et contre-écrous | 2 jeux | Une sous chaque peson, réglée avec un petit jeu (de l'ordre de 0,5 mm, selon la flèche du peson à pleine charge). C'est la seule vraie protection des pesons |
| Petit boîtier pour l'électronique | 1 | Avec une découpe pour l'afficheur |
| Masse étalon de 1 kg (classe M1) | 1 | Facultatif, si la masse actuelle n'a pas été vérifiée sur une balance de cuisine |
