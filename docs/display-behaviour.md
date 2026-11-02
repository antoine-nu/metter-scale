# Afficheur et machine à états

Ce document décrit ce que montre l'afficheur 4 chiffres. Il sert de **référence pour le firmware Arduino**. La
même logique est implémentée dans `tools/scale_logic.py` (classe `ScaleFirmware`), testée par
`tests/test_firmware.py` et utilisable sur la vraie carte avec `tools/scale_firmware_sim.py`.

## Affichage d'un poids

| Poids | Écran |
|---|---|
| entre −0,2 et +0,2 kg | `   0` |
| moins de 100 kg (après arrondi au dixième) | ` 67.4`, `  1.0`, ` -1.3` |
| 99,95 kg et plus | ` 112` (kg entiers) |
| un peson au-dessus de 80 kg pendant plus d'1 s | `  OL` |

Le point décimal ne prend pas de case : ` 67.4` occupe 4 chiffres.

## Messages

| Écran | Signification |
|---|---|
| `----` | carte pas encore prête, tare en cours, ou liaison perdue depuis plus d'1 s |
| `CAL ` | calibrage déclenché, tare à vide en cours |
| `1000` | réglage de la masse de calibrage, en grammes |
| `PL L` | poser la masse au-dessus du peson gauche |
| `PL r` | la déplacer au-dessus du peson droit |
| `donE` | calibrage réussi et enregistré (affiché 2 s) |
| `Err ` | calibrage abandonné ou incohérent, rien n'est enregistré (affiché 2 s) |
| écran éteint | arrêt automatique après 30 s à `0` |

## Mise sous tension

- La carte et l'Arduino démarrent : `----`.
- Dès que la lecture est stable à 2 kg près :
  - si la charge est proche du **zéro enregistré en EEPROM** (moins de 2 kg d'écart), ou s'il n'y a pas encore de
    zéro enregistré, la balance **refait sa tare** et affiche `0` ;
  - sinon, quelqu'un est déjà monté : la balance garde le zéro enregistré et **le pèse directement**. C'est le
    principe des pèse-personnes « step-on », compatible avec un réveil par coup de pied.

## Quand quelqu'un monte

Le but est de ne pas faire défiler des chiffres, puis de figer une valeur fiable.

| Temps après la montée | Écran |
|---|---|
| 0 à 0,6 s | ancienne valeur, le temps que les à-coups de la montée passent |
| à partir de 0,6 s | moyenne de la dernière seconde, rafraîchie toutes les 0,5 s |
| dès que c'est calme (environ 4,2 s), au plus tard à 6,5 s | **figé** sur la moyenne des 3,6 dernières secondes, avec **2 clignotements** |
| tant qu'on reste dessus | la valeur figée ne bouge plus, sauf si la moyenne s'écarte de plus de 1 kg |
| on descend | retour à `   0` |

En dessous de 2 kg (balance vide, petit objet, masse de calibrage), il n'y a pas de balancement à filtrer : la
valeur s'affiche directement.

Pas de « mémoire » de la pesée précédente : la valeur affichée est toujours la mesure réelle.

## Suivi du zéro et arrêt automatique

- **Suivi du zéro** : quand la balance affiche moins de 0,3 kg et que la lecture est très stable (variation de
  moins de 30 g sur 1 s), la tare se met à jour. Les petites dérives des pesons sont ainsi corrigées en continu.
- **Arrêt automatique** : après 30 s à `0`, l'Arduino enregistre le zéro en EEPROM puis coupe l'alimentation. En
  simulation, le programme s'arrête : le relancer revient à donner le coup de pied de réveil.

## Calibrage

Déclenché par **3 appuis brefs de la main sur le peson gauche** (moins de 0,6 s chacun, en moins de 4 s), balance
vide. Une personne qui monte ou descend ne le déclenche pas : au-delà de 30 kg, un appui est ignoré.

| Étape | Action | Écran |
|---|---|---|
| 1 | 3 appuis brefs sur le peson gauche | `CAL ` puis tare à vide |
| 2 | réglage de la masse (voir ci-dessous) | dernière masse enregistrée, par exemple `1000` |
| 3 | 4 s sans appui : la masse est retenue | elle clignote 2 fois, puis `PL L` |
| 4 | poser la masse au-dessus du peson gauche | `PL r` quand c'est enregistré |
| 5 | la déplacer au-dessus du peson droit | `donE`, puis `  1.0` avec la masse encore posée |

**Réglage de la masse avec les mains :**

| Geste | Effet |
|---|---|
| appui bref sur le peson droit | +5 g |
| appui bref sur le peson gauche | −5 g |
| appui maintenu | défile toutes les 0,2 s : 5 g par pas, puis 50 g par pas après 2,5 s |

La masse reste entre 100 et 9 995 g.

**Abandon** : 60 s sans action à une étape `PL`, ou quelqu'un qui remonte (plus de 5 kg) → `Err `, puis nouvelle
tare. Rien n'est sauvegardé. Les gains, le zéro et la masse ne sont enregistrés qu'à la fin d'un calibrage réussi.

## États

```
BOOT --(lecture stable)--> WEIGH                    tare, ou zéro enregistré si quelqu'un est déjà dessus
WEIGH --(3 appuis brefs à gauche)--> CAL_TARE       "CAL"
WEIGH --(30 s à 0)--> arrêt                         zéro enregistré en EEPROM
CAL_TARE --(balance vide stable)--> CAL_MASS        nouvelle tare à vide
CAL_MASS --(4 s sans appui)--> CAL_LEFT             masse retenue, 2 clignotements
CAL_LEFT --(masse détectée, stable)--> CAL_RIGHT
CAL_RIGHT --(masse déplacée, stable)--> WEIGH       gains calculés et enregistrés, "donE"
CAL_* --(60 s sans action, ou > 5 kg)--> BOOT       "Err", nouvelle tare
```

La lecture des voies a lieu toutes les 0,2 s. Une lecture manquée ne change rien ; après 5 lectures manquées
(1 s), l'écran affiche `----`, puis la balance repart d'elle-même quand la carte répond de nouveau.

## EEPROM

| Donnée | Écrite |
|---|---|
| gains `k0`, `k1` | à la fin d'un calibrage réussi |
| masse de calibrage | à la fin d'un calibrage réussi |
| zéro (lectures brutes des 2 voies, balance vide) | à la fin d'un calibrage réussi, et à l'arrêt automatique |

Les écritures sont rares, l'usure de l'EEPROM n'est pas un sujet.

## Réglages (constantes de `tools/scale_logic.py`)

| Constante | Valeur | Rôle |
|---|---|---|
| `POLL_PERIOD_S` | 0.2 | période de lecture de la carte |
| `BOOT_STABLE_SPREAD_KG` | 2.0 | stabilité demandée au démarrage (une personne debout doit passer) |
| `BOOT_RETARE_LIMIT_KG` | 2.0 | en dessous de cet écart au zéro enregistré, on refait la tare |
| `ZERO_BAND_KG` | 0.2 | en dessous, on affiche `0` |
| `MIN_PERSON_KG` | 2.0 | au-dessus, on filtre le balancement |
| `SETTLE_S` | 0.6 | temps ignoré après la montée |
| `REFRESH_S` | 0.5 | rafraîchissement avant que la valeur se fige |
| `SHORT_AVERAGE_SAMPLES` | 5 | moyenne affichée pendant la mesure (1 s) |
| `LOCK_AVERAGE_SAMPLES` | 18 | moyenne de la valeur figée (3,6 s) |
| `LOCK_STDEV_KG` | 0.15 | seuil de calme pour figer |
| `MAX_MEASURE_S` | 6.5 | délai maximum avant de figer |
| `RELEASE_KG` | 1.0 | écart qui libère une valeur figée |
| `BLINK_COUNT` / `BLINK_PHASE_S` | 2 / 0.2 | clignotements |
| `OVERLOAD_PAD_KG` | 80.0 | seuil `OL` par peson |
| `OVERLOAD_PERSIST_S` | 1.0 | durée de surcharge avant `OL` (une montée sur un pied ne le déclenche pas) |
| `ZERO_TRACK_KG` / `ZERO_TRACK_SPREAD_KG` | 0.3 / 0.03 | suivi du zéro |
| `AUTO_OFF_S` | 30.0 | arrêt automatique |
| `PRESS_MIN_KG` / `PRESS_RELEASE_KG` / `PRESS_MAX_KG` | 0.5 / 0.3 / 30.0 | détection d'un appui de la main |
| `PRESS_SIDE_SHARE` | 0.7 | part minimale de la charge d'un côté pour un appui |
| `HOLD_START_S` | 0.6 | au-delà, un appui est « maintenu » |
| `CAL_TRIGGER_PRESSES` / `CAL_TRIGGER_WINDOW_S` | 3 / 4.0 | déclencheur du calibrage |
| `MASS_STEP_G` / `MASS_FAST_STEP_G` / `MASS_FAST_AFTER_S` | 5 / 50 / 2.5 | réglage de la masse |
| `MASS_RANGE_G` | 100 à 9995 | bornes de la masse |
| `MASS_ACCEPT_IDLE_S` | 4.0 | validation de la masse sans appui |
| `CAL_STABLE_SAMPLES` / `CAL_STABLE_SPREAD_KG` | 8 / 0.015 | stabilité des mesures de calibrage |
| `CAL_MIN_LOAD_RATIO` | 0.2 | une masse est « posée » au-delà de 20 % de sa valeur |
| `CAL_MIN_POSITION_CHANGE` | 0.3 | écart de répartition gauche/droite exigé entre les 2 positions |
| `CAL_ABORT_KG` | 5.0 | au-delà, quelqu'un remonte : abandon |
| `CAL_STEP_TIMEOUT_S` | 60.0 | délai maximum par étape `PL` |
| `MESSAGE_S` | 2.0 | durée de `CAL`, `donE`, `Err` |
| `COMM_LOSS_POLLS` | 5 | lectures manquées avant `----` |
