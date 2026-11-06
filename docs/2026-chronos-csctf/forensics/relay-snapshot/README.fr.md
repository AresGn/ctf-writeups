---
tags: [forensics, core-dump, elf, linked-list, heap]
---

[🇬🇧 English](README.md) · 🇫🇷 Français

# Operation Dawn: Relay Snapshot

| Catégorie | Points | Résolutions | Résolu | First blood | Résolu par | Auteur du challenge |
|---|---|---|---|---|---|---|
| forensics | 125 | 42 | ✅ | — | 0xAr3s-root | Terminal43 |

## Énoncé

> Une intrusion hostile a mis hors service le relais militaire d'un pays fictif, et les
> intervenants ont capturé la mémoire du processus du relais pendant qu'ils récupéraient
> un ordre de commandement.
>
> Récupérez l'ordre complet `CSCTF{...}` depuis `relay.core`. Ce cas construit contient
> des enregistrements de relais inventés dans un vrai snapshot de processus Linux.
> Pièce jointe : `relay.core`, core ELF Linux x86-64, 586 928 octets,
> SHA-256 `b3e606bfbe727f0346be4cde683a9a8efd2680930219113a5b779a3c9a5121ac`.

**Fichiers fournis :** `files/relay.core` (non commité)

## En bref

Le tas du processus contient une liste chaînée simple de nœuds-fragments de chaînes ;
la chaîne enracinée au nœud `CSCTF` reconstitue le flag. Des chaînes leurres ont été
injectées pour perturber l'analyse.

## Démarche

**1. Reconnaissance initiale**

```bash
file relay.core    # ELF 64-bit core, x86-64
strings relay.core | grep CSCTF
```

`strings` révèle les fragments dispersés en mémoire, dans le mauvais ordre. Ils sont des
objets du tas qui doivent être parcourus via des pointeurs.

**2. Compréhension de la structure de données**

En parsant les segments PT_LOAD du fichier ELF et en cherchant les objets commençant par
`uint64 = 0x31` :

```
struct Container {
    uint64_t type;   // toujours 0x31
    struct Node {
        struct Node *next;   // VA du nœud suivant, 0 = fin de liste
        uint32_t     len;
        char         data[]; // rembourré de zéros
    } node;
};
```

Le membre `node` commence 8 octets après le début du container :
`node_va = container_va + 8`. Le champ `next` est la VA du **prochain nœud**
(= `next_container_va + 8`).

23 containers sont trouvés, chacun portant un fragment de chaîne.

**3. Reconstruction des chaînes**

On construit un graphe `node_va → (next_va, chaîne)`, puis on trouve les têtes de chaînes
(nœuds vers lesquels aucun autre nœud ne pointe) → 10 chaînes. L'une d'elles commence
au nœud `CSCTF` :

```
CSCTF → {20_ → dock → _mov → e_orc → hard_ → elm_ → grove → _dus → k_866 → 59c}
```

Les autres chaînes sont des leurres (trafic forgé dans le scénario).

```bash
python3 solve/solve.py files/relay.core
```

```
[+] FLAG chain at 0x55a7aff173c0: flag{...}
```

Script de résolution : [`solve/solve.py`](solve/solve.py)

## Flag

`flag{...}`

## Ce que j'ai appris

- `strings` révèle immédiatement les fragments, mais dans l'ordre de traversée du tas,
  pas dans l'ordre logique.
- Insight clé : les chaînes sont stockées dans une **liste chaînée simple**, pas
  contiguëment.
- Le challenge plante plusieurs chaînes leurres ; la bonne démarre au nœud `CSCTF`.
- Un parsing ELF en Python pur (sans pwntools, sans gdb) est suffisant.

## Outils et références

- `file`, `strings` (binutils)
- Python 3 (`struct`)
- Spécification ELF (System V ABI, supplément x86-64)

---
[⬅ Retour à l'événement](../../README.fr.md)
