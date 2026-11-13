# 030 — Autorité des states et contrat Recovery Kit v1

- **Statut :** DONE — contrat accepté explicitement par l'opérateur le 2026-09-25; récupération non testée
- **Permission :** READ_ONLY + OFFLINE_CODE
- **Dépendances :** six états locaux audités; revue de garde opérateur

## Objectif

Définir **une seule source de vérité** pour chaque root et le périmètre minimal d'une sauvegarde chiffrée de bootstrap. C'est un contrat et un inventaire, **pas encore l'export du kit**.

## Travail autorisé

- Classifier les six states locaux et leurs roots, notamment `pve-core-tfstate`, l'actuelle CT301 et le root historique du runner associé à l'ancien CT300.
- Identifier propriétaire, génération/lineage à enregistrer dans un manifeste **privé**, root de récupération, dépendances de secret et procédure de gel des writers.
- Vérifier en lecture seule la disponibilité et la fraîcheur du miroir GitHub; si non prouvables, conserver le statut `UNKNOWN`.
- Définir un manifeste public **sans valeurs sensibles**, une politique de nommage des générations chiffrées, un chemin de stockage indépendant et le mode de récupération du compte cloud et de la clé.
- Inventorier uniquement les inputs privés nécessaires au contrôle de l'infrastructure et les références vers des sauvegardes techniques plus volumineuses.

## Interdit

Ne pas afficher le contenu des states/inputs, exporter des secrets, publier le kit, supprimer les historiques, déplacer un backend, créer une deuxième copie active ou initier une restauration live.

## Acceptation

Chaque root a une autorité identifiée ou `UNKNOWN` explicite; l'état historique runner ne peut pas être confondu avec PostgreSQL CT300; le manifeste décrit la récupération du code, des states et des entrées privées depuis un contrôleur neuf. L'export/upload réel est réservé à la tâche 040 et à l'accord de l'opérateur.

## Livraison du contrat — 2026-09-24

Référence faisant autorité : [contrat et manifeste Recovery Kit](../docs/recovery-contract.md).
Inspection du code, des audits et des métadonnées structurelles uniquement,
sans attributs de state ou secret affichés; aucun export ni accès live.

| Critère | Preuve / limite |
| --- | --- |
| Autorité par root | Six fichiers locaux ignorés avec lineage/serial présents; quatre .backup adjacents. Tableau du contrat; autres writers/copies UNKNOWN |
| CT300 historique distinct | Root runner classé historique/recovery-only; CT301 dans migration; PostgreSQL CT300 dans tfstate. Aucun déplacement/suppression de state |
| Code indépendant | Seul remote configuré : Forgejo. URL et fraîcheur GitHub UNKNOWN; décision 040-A, aucune URL inventée |
| Inventaire et manifeste | Sources, sauvegardes, dépendances, statuts et frontière données personnelles définis; format privé sans valeurs sensibles |
| Cycle bootstrap | Ordre hors control plane défini; interface indépendante manquante explicitement réservée à 050 |
| Export et qualification | Gates de 040 définis; choix de garde et autorisation encore requis, aucun kit produit |

Les livrables documentaires sont implémentés; récupération NOT TESTED. Ne pas
confondre acceptation du contrat et résolution de chaque UNKNOWN. L'opérateur
a accepté 030; GitHub indépendant vérifié à 0ccbccb, iCloud Drive chiffré approuvé.
Les décisions et inconnues restantes sont suivies en 040, sans bloquer la
clôture du contrat documentaire. Tasks010/020 inchangées; backend non choisi.

Validation documentaire : sept fichiers Markdown, 64 liens relatifs/ancres et
blocs de code vérifiés; check-quality.py PASS (51 YAML, 6 Python, 18 shell);
git diff --check PASS. Audits historiques inchangés. Aucun test de récupération,
export, migration, restore ou commande live exécuté.
