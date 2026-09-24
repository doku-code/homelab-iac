# 030 — Autorité des states et contrat Recovery Kit v1

- **Statut proposé :** READY après 000; indépendant de la CI qualité
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
