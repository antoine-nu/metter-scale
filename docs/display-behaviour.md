# Afficheur et machine à états

Ce document décrit ce que montre l'afficheur 4 chiffres. Il sert de **référence pour le firmware Arduino**. La
même logique est implémentée dans `tools/scale_firmware_sim.py` (classe `ScaleFirmware`), testée par
`tests/test_firmware.py`.

## Affichage d'un poids

| Poids | Écran |
|---|---|
| entre −0,2 et +0,2 kg | `   0` |
| moins de 100 kg (après arrondi au dixième) | ` 67.4`, `  1.0`, ` -1.3` |
| 99,95 kg et plus | ` 112` (kg entiers) |
| un peson au-dessus de 60 kg | `  OL` |

Le point décimal ne prend pas de case : ` 67.4` occupe 4 chiffres.

## Messages

| Écran | Signification |
|---|---|
| `----` | carte pas encore prête, tare en cours, ou liaison perdue depuis plus d'1 s |
| `CAL ` | calibrage déclenché, tare à vide en cours |
| `PL L` | poser la masse au-dessus du peson gauche |
| `PL r` | la déplacer au-dessus du peson droit |
| `donE` | calibrage réussi et enregistré (affiché 2 s) |
| `Err ` | calibrage abandonné ou incohérent, rien n'est enregistré (affiché 2 s) |

## Quand quelqu'un monte

Le but est de ne pas faire défiler des chiffres, puis de figer une valeur fiable.

| Temps après la montée | Écran |
|---|---|
| 0 à 0,6 s | ancienne valeur, le temps que les à-coups de la montée passent |
| à partir de 0,6 s | moyenne de la dernière seconde, rafraîchie toutes les 0,5 s |
| dès que c'est calme, au plus tard à 5 s | **figé** sur la moyenne des 2 dernières secondes, avec **2 clignotements** |
| tant qu'on reste dessus | la valeur figée ne bouge plus, sauf si la moyenne s'écarte de plus de 1 kg |
| on descend | retour à `   0` |

En dessous de 2 kg (balance vide, petit objet, masse de calibrage), il n'y a pas de balancement à filtrer : la
valeur s'affiche directement.

Exemple sur la balance simulée, personne de 76 kg qui se balance de ±300 g :

```
  0.8s  [ 76.0]
  1.4s  [ 76.2]
  2.0s  [ 76.1]
  2.6s  [     ]   figé : extinction 1
  2.8s  [ 76.1]
  3.0s  [     ]   extinction 2
  3.2s  [ 76.1]   valeur définitive
```

## États

```
BOOT --(lecture stable à 2 kg près)--> WEIGH            tare = moyenne des dernières lectures
WEIGH --(poids stable <= -40 kg)--> CAL_TARE            geste de calibrage
CAL_TARE --(balance vide stable)--> CAL_LEFT            nouvelle tare à vide
CAL_LEFT --(masse détectée, stable)--> CAL_RIGHT
CAL_RIGHT --(masse déplacée, stable)--> WEIGH           gains calculés et enregistrés, "donE"
CAL_* --(60 s sans action, ou > 5 kg)--> BOOT           "Err", nouvelle tare
```

La lecture des voies a lieu toutes les 0,2 s. Une lecture manquée ne change rien ; après 5 lectures manquées
(1 s), l'écran affiche `----`, puis la balance repart d'elle-même quand la carte répond de nouveau.

## Réglages (constantes)

| Constante | Valeur | Rôle |
|---|---|---|
| `POLL_PERIOD_S` | 0.2 | période de lecture de la carte |
| `BOOT_STABLE_SPREAD_KG` | 2.0 | stabilité demandée pour la tare de démarrage (une personne debout doit passer) |
| `ZERO_BAND_KG` | 0.2 | en dessous, on affiche `0` |
| `MIN_PERSON_KG` | 2.0 | au-dessus, on filtre le balancement |
| `SETTLE_S` | 0.6 | temps ignoré après la montée |
| `REFRESH_S` | 0.5 | rafraîchissement avant que la valeur se fige |
| `SHORT_AVERAGE_SAMPLES` | 5 | moyenne affichée pendant la mesure (1 s) |
| `LOCK_AVERAGE_SAMPLES` | 10 | moyenne de la valeur figée (2 s) |
| `LOCK_STDEV_KG` | 0.15 | seuil de calme pour figer |
| `MAX_MEASURE_S` | 5.0 | délai maximum avant de figer |
| `RELEASE_KG` | 1.0 | écart qui libère une valeur figée |
| `BLINK_COUNT` / `BLINK_PHASE_S` | 2 / 0.2 | clignotement à la fin de la mesure |
| `OVERLOAD_PAD_KG` | 60.0 | seuil `OL` par peson |
| `CAL_TRIGGER_KG` | −40.0 | déclencheur du calibrage |
| `CAL_STABLE_SAMPLES` / `CAL_STABLE_SPREAD_KG` | 8 / 0.015 | stabilité demandée pour les mesures de calibrage |
| `CAL_MIN_LOAD_RATIO` | 0.2 | une masse est « posée » au-delà de 20 % de sa valeur |
| `CAL_MIN_POSITION_CHANGE` | 0.3 | écart de répartition gauche/droite exigé entre les 2 positions |
| `CAL_ABORT_KG` | 5.0 | au-delà, quelqu'un remonte : abandon |
| `CAL_STEP_TIMEOUT_S` | 60.0 | délai maximum par étape de calibrage |
| `MESSAGE_S` | 2.0 | durée d'affichage de `CAL`, `donE`, `Err` |
| `COMM_LOSS_POLLS` | 5 | lectures manquées avant `----` |
