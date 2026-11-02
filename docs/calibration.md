# Calibrage

## Pourquoi calibrer côté Arduino

La carte a été calibrée pour d'autres pesons. Mesures sur la vraie carte (voir
[relevés](measurements/2026-11-01-board-readings.md)) :

| Voie | Zéro à vide | Valeur réelle d'une unité lue |
|---|---|---|
| 0 (droite) | +3554 | environ 0,59 g (la carte surestime d'environ 1,7 fois) |
| 1 (gauche) | −1091 (statut `I`) | environ 3,74 g (la carte sous-estime d'environ 3,7 fois) |

Plutôt que de réécrire le calibrage de la carte, l'Arduino corrige les lectures brutes :

```
poids = k0 × (voie0 − zéro0) + k1 × (voie1 − zéro1)
```

- `zéro0` et `zéro1` : la tare, faite à chaque mise sous tension.
- `k0` et `k1` : les gains, mesurés une fois par le calibrage et gardés en EEPROM.

Les pesons sont linéaires : une tare et un seul delta connu par peson suffisent.

## Principe « 1 masse, 2 positions »

Balance vide, on pose une masse connue `m` à deux endroits différents, près du peson gauche puis près du peson
droit. On enregistre à chaque fois la variation des deux voies, ce qui donne deux équations :

```
k0 × a0 + k1 × a1 = m      (masse côté gauche)
k0 × b0 + k1 × b1 = m      (masse côté droit)
```

L'Arduino résout ce système. Avantages :

- La masse n'a pas besoin d'être pile au-dessus d'un peson : le système tient compte de la répartition.
- Les deux gains sont alignés : le poids affiché ne dépend plus de l'endroit où l'on se tient.
- Personne n'est sur la balance pendant la mesure : pas de bruit dû au balancement.

Le calcul est refusé (`Err`) si les deux positions sont trop proches, ou si un gain sort de la plage
plausible (0,01 à 100 g par unité).

## Procédure (geste utilisateur)

Balance allumée et vide, affichant `0` :

| Étape | Action | Écran |
|---|---|---|
| 1 | **3 appuis brefs de la main sur le peson gauche** (en moins de 4 s) | `CAL ` (tare à vide) |
| 2 | Régler la masse : appui bref à droite +5 g, à gauche −5 g ; appui maintenu pour défiler | la masse en grammes, par exemple `1000` |
| 3 | Ne plus toucher pendant 4 s | la masse clignote 2 fois, puis `PL L` |
| 4 | Poser la masse au-dessus du peson gauche | `PL r` quand c'est enregistré |
| 5 | La déplacer au-dessus du peson droit | `donE` |
| 6 | La masse est encore posée | `  1.0` : vérification immédiate |

- La masse proposée au départ est la dernière enregistrée (1000 g la première fois).
- Une personne qui monte ou descend ne déclenche pas le calibrage : au-delà de 30 kg, un appui est ignoré.
- **Abandon** : 60 s sans action à une étape `PL`, ou quelqu'un qui remonte (plus de 5 kg) → `Err `, puis nouvelle
  tare. Rien n'est sauvegardé.
- Les gains, la masse et le zéro ne sont enregistrés qu'à la fin d'un calibrage réussi.

Avant tout premier calibrage, les gains valent 1 et la voie gauche sous-estime le poids d'environ 3,7 fois : un appui
de 5 kg à gauche n'est vu qu'à 1,3 kg. Il faut donc **appuyer franchement** (au moins 2 kg réels) pour que les
appuis soient détectés.

## Masse de référence et précision

- Un paquet « 1 kg » du commerce peut s'écarter d'environ 1,5 %. Il faut une masse étalon, ou une masse pesée sur
  une balance de cuisine, et régler sa valeur exacte à l'étape 2.
- La voie gauche a une résolution d'environ 3,7 g par unité. Avec 1 kg, la précision attendue est d'environ ±0,1 à
  0,2 kg sur le poids d'une personne. Une masse de 2 à 5 kg l'améliore.
- Si ce n'est pas suffisant, l'option suivante est de refaire le calibrage natif de la carte sur les voies 0 et 1
  (commandes `B`, `C`, `E`, `F`) pour retrouver 1 g par unité. Cela écrit dans l'EEPROM de la carte.
