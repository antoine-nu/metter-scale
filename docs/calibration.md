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

| Étape | Action | Écran |
|---|---|---|
| 1 | Monter sur la balance, la mettre sous tension | `----` puis `   0` |
| 2 | **Attendre le `0`**, puis descendre | `CAL ` (tare à vide) |
| 3 | Poser la masse au-dessus du peson gauche | `PL L`, puis `PL r` quand c'est enregistré |
| 4 | La déplacer au-dessus du peson droit | `donE` |
| 5 | La masse est encore posée | `  1.0` : vérification immédiate |

- **Déclencheur** : un poids stable inférieur à **−40 kg par rapport au zéro du démarrage**. Ça n'arrive que si
  quelqu'un était sur la balance à l'allumage puis descend. Une descente normale ne le déclenche jamais.
- **Abandon** : 60 s sans action à une étape, ou quelqu'un qui remonte (plus de 5 kg) → `Err `, puis nouvelle
  tare. Rien n'est sauvegardé.
- Les gains ne sont enregistrés qu'à la fin d'un calibrage réussi.

Avant tout premier calibrage, les gains valent 1 et les poids affichés sont faux. Il faut alors rester **bien
centré** pendant le geste : la voie gauche sous-estime fortement le poids, et avec tout le poids sur le peson
gauche une personne de 96 kg n'est vue qu'à 26 kg, sous le seuil de 40 kg.

## Masse de référence et précision

- Un paquet « 1 kg » du commerce peut s'écarter d'environ 1,5 %. Il faut une masse étalon, ou une masse pesée sur
  une balance de cuisine, et indiquer sa valeur exacte (`--mass` dans le simulateur, constante dans le firmware).
- La voie gauche a une résolution d'environ 3,7 g par unité. Avec 1 kg, la précision attendue est d'environ ±0,1 à
  0,2 kg sur le poids d'une personne. Une masse de 2 à 5 kg l'améliore.
- Si ce n'est pas suffisant, l'option suivante est de refaire le calibrage natif de la carte sur les voies 0 et 1
  (commandes `B`, `C`, `E`, `F`) pour retrouver 1 g par unité. Cela écrit dans l'EEPROM de la carte.
