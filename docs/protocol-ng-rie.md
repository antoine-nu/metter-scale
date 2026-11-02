# Protocole de la carte Mettler Toledo NG-RIE

Synthèse de la spécification constructeur « NG-RIE AutoShelf Communication Protocol V0.09 », complétée par ce qui
a été observé sur la vraie carte (firmware `Speedy V0.03`). En cas de divergence, **le comportement observé fait foi**.

## Liaison

- RS-485 half-duplex, **9600 bauds, 8 bits, pas de parité, 1 bit de stop**.
- Maître / esclave : on envoie une commande, la carte répond. Elle ne parle jamais d'elle-même.
- Le câble FTDI USB-RS485 utilisé sur PC ne renvoie pas d'écho de ce qu'il émet. Les outils tolèrent quand même un
  écho (certains adaptateurs en produisent).

## Trame

```
F2 | L | commande + données | C | F3
```

- `F2` : début de trame, `F3` : fin de trame.
- `L` : nombre d'octets qui suivent `L`, jusqu'à `F3` inclus (données + C + F3).
- `C` : XOR de tous les octets de `L` (inclus) jusqu'à `C` (exclu). `F2` n'entre pas dans le calcul.
- **Pas d'échappement** : `C` peut valoir `F2` ou `F3`. Une trame se délimite donc par sa longueur `L`, jamais en
  cherchant `F3`.
- Les réponses reprennent la lettre de la commande en **minuscule** (`A` → `a`, `T` → `t`).
- Erreur : lettre minuscule + `E` + numéro, par exemple `oE12`.

Exemples vérifiés sur la carte :

| Commande | Trame envoyée | Réponse |
|---|---|---|
| Demander l'ID | `F2 03 41 42 F3` (`A`) | `F2 07 61 30 30 30 32 64 F3` (`a0002`) |
| Version | `F2 07 56 30 30 30 32 53 F3` (`V0002`) | `vSpeedy V0.03;BL 72263789 V0.03` |

## Identifiant de la carte

`nnnn` = **4 caractères ASCII** (ici `0002`). On l'obtient avec `A` (un seul appareil sur le bus) et on le répète
dans toutes les autres commandes.

## Commandes utiles

`N` ou `p` désigne un numéro de voie (« pad ») en ASCII : `0` à `9`, puis `A`, `B`.

| Rôle | Commande | Réponse | Écrit dans la carte ? |
|---|---|---|---|
| ID de la carte | `A` | `a nnnn` | non |
| Version firmware | `V nnnn` | `v ...` | non |
| Numéro de série | `1 nnnn 1` | `0` + 16 caractères | non |
| Nom (alias) | `1 nnnn 3` | `0` + 16 caractères | non |
| Nombre de voies | `1 nnnn 4` | `0` + 2 chiffres (ici `06`) | non |
| Modèle prédéfini (mode étagère) | `Q nnnn` | `q` + modèle, ou `qPADMODE` | non |
| Configuration d'une voie | `Q nnnn # p` | `q ddddd ccccc uu` | non |
| Masse de calibrage d'une voie | `O nnnn # p` | `o` + masse | non |
| **Poids des voies 0 à N-1** | `T nnnn N` | `t N` + N champs de poids | non |
| Poids d'une voie | `W nnnn N` | `w` + 1 champ de poids | non |
| Mise à zéro d'une voie | `Z nnnn N` | `zZ` | **oui** |
| Configurer une voie | `M nnnn # p ddddd ccccc uu` | `m ...` | **oui** |
| Calibrage natif | `B` (masse), puis `C`, `E`, `F` | `cU` → `eF` → `fC` | **oui** |
| Changer l'ID | `S`, `I` | | **oui** |
| Reset | `R nnnn` | `r nnnn` | |

Les outils de ce dépôt n'utilisent que les commandes en lecture.

### Champ de poids (10 caractères)

```
s wwwwwwww x
```

- `s` : signe, espace ou `-`. `E` signale une erreur, et `wwwwwwww` contient alors son numéro.
- `wwwwwwww` : poids complété de zéros à gauche, point décimal inclus. **Unité observée : le gramme.**
- `x` : statut. Espace = OK, `M` = en mouvement, `C` = surcharge, `I` = poids invalide.

Exemple (illustratif, le remplissage exact n'a pas encore été relevé en trame brute) : `t2` + ` 003554.0 ` +
`-001091.0I` donne voie 0 = 3554 g (OK) et voie 1 = −1091 g (invalide).

## Configuration d'une voie (mode « pad »)

`ddddd` est la valeur d'une division en milligrammes (0,001 × ddddd g). `ccccc` est la capacité exprimée en
divisions. Avec `01000` / `20000` : 1 division = 1 g, capacité 20 000 g. Une configuration `0000000000` désactive
la voie.

## Codes d'erreur

| Code | Signification |
|---|---|
| 1 | erreur de peson |
| 2 | données de calibrage absentes |
| 3 | en mouvement |
| 4 | modèle non configuré |
| 5 | numéro de voie incorrect |
| 6 | erreur de commande |
| 7 | erreur de lecture/écriture EEPROM |
| 8 | masse de calibrage incorrecte |
| 10 | voie désactivée |
| 11 | commande de voie impossible en mode étagère |
| 12 | commande d'étagère impossible en mode voie |
| PW | carte en cours de démarrage, réessayer dans quelques secondes |

## Écarts constatés avec la documentation

| Point | Doc | Observé |
|---|---|---|
| Réponse à `Q nnnn # p` | `m ...` | `q0100020000uu` |
| Réponse à `1 nnnn 4` (nombre de voies) | `I nn` | `006` |
| Unité des poids | non précisée | grammes |
| Séparateurs `\|` entre champs de poids | dessinés dans la doc | absents (les outils acceptent les deux) |
| Voies 6 à B | décrites | `E5` : la carte n'a que 6 voies |
| Statut `C` au-delà de la capacité configurée | attendu | non vu : la voie 0 a renvoyé 166 533 g (capacité 20 000) sans `C`, toujours en `M` |
| Démarrage | réponse `PW` | la carte peut aussi rester **muette** quelques secondes : les outils réessaient pendant 10 s |
