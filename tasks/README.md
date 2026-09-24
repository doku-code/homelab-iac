# Tâches de `homelab-iac`

> **But :** garder l'agent concentré sur un périmètre vérifiable. La [roadmap](../docs/roadmap.md) décrit *l'ordre et les dépendances*; chaque tâche décrit *ce qu'il est autorisé à faire maintenant*. L'[architecture](../docs/architecture.md) explique les frontières durables. Les [audits du 2026-09-24](../docs/audits/2026-09-24/executive-summary.md) sont des preuves historiques.

## Comment utiliser ce dossier

- Une tâche a un identifiant stable, un statut, des prérequis, des fichiers concernés, une liste de travaux **autorisés**, des interdictions et des critères d'acceptation observables.
- L'agent commence par lire `AGENTS.md`, les documents de référence, **une seule tâche assignée** et l'état Git. Il n'exécute pas spontanément le prochain milestone.
- La tâche peut être découpée en commits ciblés sans perdre son objectif. Les erreurs et prérequis manquants doivent être remontés au lieu d'être contournés.
- Après revue, mettre à jour le statut et joindre les preuves/commits. Ne pas marquer `DONE` parce que du code a été écrit; les critères doivent être vérifiés.

**Statuts :** `PLANNED` (proposé), `READY` (pré requis de code/révision suffisants), `IN_PROGRESS` (assigné), `BLOCKED` (action/autorisation manquante), `DONE` (accepté par l'opérateur). Ces statuts dans les fichiers sont **proposés au moment de leur préparation**, pas un résultat live.

**Permissions :** `READ_ONLY`, `OFFLINE_CODE`, `LIVE_READ`, `LIVE_CHANGE`, `DESTRUCTIVE_DRILL`. Un statut `READY` n'autorise jamais une catégorie `LIVE_CHANGE` ou `DESTRUCTIVE_DRILL` sans accord explicite sur les ressources et l'opération.

## File d'exécution recommandée

| Ordre | Tâche | Statut initial | Permissions au départ |
| --- | --- | --- | --- |
| 00 | [Intégrer la baseline](000-project-baseline.md) | READY | OFFLINE_CODE |
| 01 | [Frontière de sécurité du runner](010-runner-trust-preflight.md) | READY après 00 | READ_ONLY + OFFLINE_CODE |
| 02 | [CI qualité sans secrets](020-ci-quality.md) | PLANNED après 01 | OFFLINE_CODE |
| 03 | [Contrat d'autorité des states](030-state-recovery-contract.md) | READY après 00; parallèle à 01–02 | READ_ONLY + OFFLINE_CODE |
| 04 | [Recovery Kit v1](040-recovery-kit-v1.md) | BLOCKED par 03 et décisions de garde | Préparation hors ligne; export/upload séparément autorisés |
| 05 | [Contrôleur bootstrap](050-independent-controller.md) | PLANNED après 04 | OFFLINE_CODE; drill séparé |
| 06 | [Compléter PostgreSQL](060-postgresql-candidate.md) | BLOCKED par sécurité/récupération et identités | Autorisations live ciblées |
| 07 | [Laboratoire Consul](070-consul-candidate.md) | PLANNED, allocation à autoriser | Test isolé uniquement |
| 08 | [Backend → récupération → canari → CD](080-control-plane-and-cd.md) | PLANNED | Jalons/approbations séparés |
| 09 | [Premier composant réutilisable](090-reusable-lxc.md) | PLANNED après CI + contrat state | OFFLINE_CODE puis environnement jetable |

**Chemin critique :** 00 → 01 → 02 donne la CI de qualité rapidement. 00 → 03 → 04 → 05 protège le bootstrap. Le backend final, la récupération du control plane et la CD ne peuvent pas être promus par une validation syntaxique seule.

## Template minimal pour une future tâche

```markdown
# <ID> — <Titre>

- Statut : PLANNED
- Permission initiale : READ_ONLY / OFFLINE_CODE / LIVE_READ / LIVE_CHANGE / DESTRUCTIVE_DRILL
- Dépendances : ...
- Contexte et preuves : chemins exacts + limites de l'audit
- Objectif : ...
- Autorisé : ...
- Interdit : ...
- Critères d'acceptation : ...
- Vérifications et rapport : ...
- Autorisation opérateur requise : ...
```

Ne pas inclure de secrets, states, clés ou détails de récupération sensibles dans les tâches publiques.
