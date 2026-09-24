# 080 — Backend choisi, control plane récupérable, canari puis CD protégée

- **Statut proposé :** PLANNED — tâche *epic*, à découper avant toute implémentation
- **Permission :** décision/documentation uniquement pour l'epic; chaque opération live exige une tâche séparée
- **Dépendances :** 020, 030–050, 060–070, inventaire de récupération des fondations

## Objet

Décrire la chaîne de décisions, pas lancer un déploiement massif. Les sous-milestones doivent rester séparés et ordonnés.

### 080-A — Sélection et contrat de migration

Après les qualifications PostgreSQL/Consul, fixer backend, limites de disponibilité, secrets, isolation des roots et récupération hors de lui-même. Choisir un canari **non-bootstrap**. Aucun code produit ici ne vaut approbation de migration.

### 080-B — Drill indépendant du control plane

Dans des allocations isolées approuvées, prouver la récupération des prérequis physiques/techniques pertinents, des états et identités, de Forgejo/registre et de CT301 depuis un contrôleur neuf. Pas de copie de runner active avec les mêmes identifiants contre la production. L'essai doit inclure une image réellement disponible et un job inoffensif.

### 080-C — Canary state

Geler les writers, sceller l'état exact, vérifier lineage/serial et destination, migrer un seul root non-bootstrap, produire un plan sans recréation, valider locking entre contrôleurs et interdire un ancien state local writable après hand-back. Aucun refactoring de module dans cette migration.

### 080-D — CD protégée

Débuter par un `plan` sur références approuvées, root allowlist, identité minimale, logs expurgés et state obligatoire; seulement ensuite autoriser un `apply` séparé associé au plan approuvé et à une fenêtre explicitement autorisée. Le pipeline Q2 reste sans credentials.

## Critère final

Le runner restauré peut appliquer un changement jetable approuvé via un backend faisant autorité et Infisical, tout en conservant un chemin bootstrap indépendant. **Ne pas marquer cet epic DONE avant les quatre tâches acceptées séparément.**
