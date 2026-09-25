# 000 — Intégrer la baseline d'architecture et les règles de travail

- **Statut :** DONE — intégration acceptée par l'opérateur le 2026-09-24
- **Permission :** OFFLINE_CODE, documentation uniquement
- **Dépendances :** audit `docs/audits/2026-09-24/` et revue de l'opérateur

## Objectif

Intégrer `docs/architecture.md`, `docs/roadmap.md`, `tasks/` et une version **fusionnée** du vrai `AGENTS.md`. Les propositions générées hors dépôt ne constituent pas la version finale tant que l'AGENTS original n'a pas été examiné. Faire de la roadmap et des tâches la référence d'exécution, sans perdre les règles de sécurité en place.

## Travail autorisé

- Lire l'AGENTS local, le README et les six fichiers d'audit; vérifier que les liens relatifs fonctionnent après intégration.
- Comparer les consignes fournies au fichier local **sans écraser** des instructions existantes. L'opérateur a confirmé que les fichiers déjà présents dans `tasks/`, `docs/` et `AGENTS.md` constituent le lot d'intégration; aucun fichier `AGENTS.proposed.md` ni ZIP supplémentaire n'est requis.
- Vérifier `git status`, le remote GitHub et la fraîcheur réelle de sa copie **en lecture seule**. Constater, sans pousser, les commits locaux et les fichiers non suivis.
- Garder l'audit comme archive historique au baseline `fd4435e`; ajouter des corrections postérieures dans les documents vivants plutôt que réécrire les preuves historiques.

## Interdit

Aucun Terraform/Ansible live, push automatique, state export, migration, secret ou écrasement non revu de l'AGENTS actuel. Les commits documentaires explicitement autorisés sont permis après revue ciblée. Ne pas utiliser `git add -A` sur des fichiers non revus.

## Acceptation

- Tous les documents nécessaires sont présents, non contradictoires et leurs liens résolvent dans le dépôt.
- `AGENTS.md` original et nouvelles règles ont été fusionnés et approuvés.
- Statut Git et fraîcheur GitHub qualifiés (confirmés ou `UNKNOWN`), sans publication implicite.
- Un seul premier travail d'implémentation est assigné : tâche 010, puis 020 après le gate de sécurité.

## Preuves d'intégration — 2026-09-24

Les six rapports historiques sont conservés dans le commit `627a0a0`.
Le nouveau contrat opérateur autorise explicitement le suivi Git d'AGENTS.md;
aucune règle d'ignore applicable n'a été trouvée. Les mentions « local-only »
dans l'audit décrivent uniquement la politique au baseline `fd4435e`.
Le seul remote configuré est Forgejo; publication GitHub toujours UNKNOWN.
L'opérateur a confirmé l'intégration et l'implémentation CI initiale complètes
dans la demande de contrat de maintenance. Les liens ont été vérifiés; AGENTS.md
est suivi dans `f2a1b8d`. Cela clôt 000, pas les critères live des tâches 010/020.
Aucun push ou changement de production n'est autorisé par cette acceptation.
