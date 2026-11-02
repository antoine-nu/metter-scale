# Relevés sur la vraie carte (1er novembre 2026)

Carte NG-RIE alimentée en 12 V, 2 pesons de 50 kg branchés, PC relié par câble FTDI USB-RS485 (COM7).

## Identité et configuration (`ng_rie_probe.py info`)

```
Board ID: b'0002'
Firmware version          b'vSpeedy V0.03;BL 72263789 V0.03'
Serial number             b'0                '
Alias name                b'0                '
Channel counts            b'006'
Model (shelf mode)        b'qPADMODE\x00'
Calibration weight        b'oE12'
Pad 0 config              b'q0100020000uu'    Pad 0 calibration weight  b'o1000.000000'
Pad 1..5 config           b'q0100020000uu'    Pad 1..5 calibration weight b'o1500.000000'
Pad 6..B config           b'qE5 '
```

Lecture :

- ID `0002` (ASCII), mode « pad », 6 voies.
- Chaque voie : 1 g par division, capacité 20 kg.
- La voie 0 a été calibrée avec 1000 g, les autres avec 1500 g.
- `oE12` : erreur 12, normale en mode pad.

Cette sortie sert de **sauvegarde de la configuration d'origine**.

## Voies au repos (`ng_rie_probe.py watch --channels 6`)

| Voie | Valeur | Statut | Conclusion |
|---|---|---|---|
| 0 | 3553 à 3554 | OK | peson droit |
| 1 | −1090 à −1091 | `I` | peson gauche |
| 2 | −1507 | `I` | rien de branché |
| 3 | −1650 | `I` | rien de branché |
| 4, 5 | `E2` | | jamais calibrées |

- Bruit au repos : ±1 unité.
- Après une charge, dérive (fluage) de 5 à 20 unités qui se résorbe en quelques secondes.

## Masse posée à gauche puis à droite

| Position | Δ voie 0 | Δ voie 1 |
|---|---|---|
| gauche | +105 | +251 |
| droite | +1664 | +6 |

En supposant une masse de 1000 g, la résolution du système donne `k0 = 0,588` et `k1 = 3,738` g par unité.

## Personne debout

- La carte signale `M` (en mouvement) en permanence : la stabilité doit être détectée par l'Arduino.
- La voie 0 est montée à 166 533 sans écrêtage ni statut `C`, bien au-delà de la capacité configurée (20 kg).
- Le rapport de gains, mesuré indépendamment en se penchant d'un côté à l'autre, vaut environ 6,0 (6,4 avec la
  masse). Avec la correction, la somme reste stable à ±1 % alors que la répartition varie fortement : **le
  principe du calibrage en 2 positions est validé**.

## Point ouvert

Avec ces gains, la personne pesait **168 kg**, ce qui est peu plausible. Hypothèses : la masse ne pesait pas
1000 g, ou la première pose a été mal faite (somme brute 356 contre 1670 pour la seconde).

Un second essai avec le calibrage du simulateur a affiché environ **96 kg**. Le poids réel de la personne n'a pas
encore été comparé à une balance de référence : la justesse absolue reste à valider.

## Répétabilité (2 novembre 2026)

Avec le simulateur calibré, plusieurs montées successives de la même personne se sont figées à 93,4, 93,3 puis
93,2 kg : ±0,1 kg, soit la limite d'un affichage au dixième. En réponse :

- moyenne de la valeur figée allongée de 2 s à 3,6 s ;
- suivi automatique du zéro quand la balance est vide.

Pas de « mémoire » de la pesée précédente : on garde la mesure réelle.

## Temps de démarrage de la carte

Entre la mise sous tension du 12 V et le retour des poids dans `watch` : **2 à 3 s**. C'est le délai minimal entre
le réveil de la balance et l'affichage du `0`.
