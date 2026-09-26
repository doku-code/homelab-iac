# Tâches de `homelab-iac`

> **But :** garder l'agent concentré sur un périmètre vérifiable. La [roadmap](../docs/roadmap.md) décrit *l'ordre et les dépendances*; chaque tâche décrit *ce qu'il est autorisé à faire maintenant*. L'[architecture](../docs/architecture.md) explique les frontières durables. Les [audits du 2026-09-24](../docs/audits/2026-09-24/executive-summary.md) sont des preuves historiques.

## Comment utiliser ce dossier

- Une tâche a un identifiant stable, un statut, des prérequis, des fichiers concernés, une liste de travaux **autorisés**, des interdictions et des critères d'acceptation observables.
- L'agent commence par lire `AGENTS.md`, les documents de référence, **une seule tâche assignée** et l'état Git. Il n'exécute pas spontanément le prochain milestone.
- La tâche peut être découpée en commits ciblés sans perdre son objectif. Les erreurs et prérequis manquants doivent être remontés au lieu d'être contournés.
- Après revue, mettre à jour le statut et joindre les preuves/commits. Ne pas marquer `DONE` parce que du code a été écrit; les critères doivent être vérifiés.

**Statuts :** `PLANNED` (proposé), `READY` (pré requis de code/révision suffisants), `IN_PROGRESS` (assigné), `BLOCKED` (action/autorisation manquante), `DONE` (accepté par l'opérateur). Ces statuts dans les fichiers sont **proposés au moment de leur préparation**, pas un résultat live.

**Permissions :** `READ_ONLY`, `OFFLINE_CODE`, `LIVE_READ`, `LIVE_CHANGE`, `DESTRUCTIVE_DRILL`. Un statut `READY` n'autorise jamais une catégorie `LIVE_CHANGE` ou `DESTRUCTIVE_DRILL` sans accord explicite sur les ressources et l'opération.

## Contrat de maintenance

Chaque tâche d'implémentation doit avoir un statut courant, des critères
d'acceptation explicites et des preuves datées. Le fichier de tâche fait autorité
pour son avancement; les tableaux de statuts initiaux restent historiques.

1. Avant de commencer, inspecter Git, le code pertinent, la tâche active,
   l'architecture, la roadmap et les runbooks concernés.
2. Pendant le travail, maintenir la tâche : progrès, critères vérifiés ou non,
   dépendances découvertes, blocages et prochaine action/autorisation nécessaire.
3. Avant clôture, mettre à jour les documents affectés selon le tableau ci-dessous.
   Si aucun document supplémentaire n'est affecté, l'indiquer dans la tâche.
4. Ne marquer une tâche ou un milestone DONE qu'après vérification de tous ses
   critères et acceptation opérateur. Un critère live non testé reste non vérifié;
   du code committé ou un blocage documenté ne constitue pas un PASS implicite.
5. Inclure les mises à jour documentaires directement liées dans le commit
   d'implémentation lorsque possible; expliquer tout suivi séparé dans la tâche.
   Vérifier liens et diff avant commit. Ne jamais dupliquer un runbook complet
   dans plusieurs fichiers : résumer et lier la référence faisant autorité.

| Changement | Document à maintenir |
| --- | --- |
| Avancement, preuves, critères, blocages | Tâche active dans tasks/ |
| Statut, dépendances ou périmètre d'un milestone | docs/roadmap.md, avec lien vers la tâche |
| Architecture réelle ou décision architecturale approuvée | docs/architecture.md, en distinguant cible et implémentation |
| Entrées du projet, prérequis, workflows supportés ou capacités majeures | README.md racine |
| Nouvelle référence ou déplacement documentaire | docs/README.md et liens concernés |
| Procédure ou comportement opérationnel | Runbook concerné |
| Évolution après un audit daté | Nouvelle preuve ou document vivant; ne pas réécrire l'audit |

Le niveau de preuve est distinct du statut de tâche : **PLANNED** = intention;
**IMPLEMENTED** = code présent; **LOCALLY VALIDATED** = commandes locales et
résultats datés; **LIVE VERIFIED** = exécution réelle identifiée, environnement
et limites enregistrés. Aucun niveau n'implique automatiquement le suivant.
Les permissions live demeurent séparées de ces statuts.

## Current reconstruction queue

The [canonical roadmap](../docs/roadmap.md) supersedes the old backend-first and
LXC-first order. Existing task history is retained; SUPERSEDED/DEFERRED never
authorizes deletion of infrastructure or state. ADAPTED means scope changed,
not acceptance achieved. PLANNED tasks need assignment and any live approval.

| Task | Current responsibility | Status / gate |
| --- | --- | --- |
| [000](000-project-baseline.md) | Historical governance integration | DONE; original next-task order is historical |
| [010](010-runner-trust-preflight.md) / [020](020-ci-quality.md) | Runner security / working quality CI | Security closure BLOCKED, functional CI live verified |
| [030](030-state-recovery-contract.md) | Single state authority / independent custody | DONE accepted contract, not recovery proof |
| [035](035-headless-controller.md) | Optional recovery VM test adapter | DEFERRED; previous preflight intact, no allocation/plan approved |
| [040](040-recovery-kit-v1.md) | Production kit capture/retrieval | ADAPTED; synthetic preparation exists, production gates blocked |
| [050](050-independent-controller.md) | Portable Mac/Linux synthetic controller | PLANNED; parallel to100 after assignment, no full-kit prerequisite |
| [060](060-postgresql-candidate.md) / [070](070-consul-candidate.md) | Conditional backend experiments | DEFERRED to requirements-led080, not compulsory comparison |
| [080](080-control-plane-and-cd.md) | Backend need/qualification, separate canary and protected CD | PLANNED after security/recovery gates |
| [090](090-reusable-lxc.md) | Historical generic LXC-first proposal | SUPERSEDED as prerequisite by100; live CTs untouched |
| [100](100-stage-a-headless-vms.md) | Three new headless server VM profiles | DONE / operator accepted live evidence for guests303-305 and second convergence |
| [110](110-k3s-lifecycle.md) | K3s bootstrap/lifecycle/synthetic recovery | After100 guests and separately approved live actions |
| [120](120-gitops-stateless.md) | Flux/stateless demo/measurements | After110 and source/RBAC review |
| [130](130-storage-recovery.md) | TrueNAS protocols/fencing/synthetic DB restore | After120 and storage approvals |
| [140](140-placement-and-cutover.md) | Distributed/permanent placement and individual service DR/cutover | Epic split into bounded tasks before execution |

Critical path: architecture review ->100 ->110 ->120 ->130 ->140.
Parallel recovery path:050 synthetic ->040 real kit ->140 production DR.
Production data never moves before its own independently qualified recovery.
080 gates shared backend/privileged infrastructure automation; not disposable
stateless learning. No task starts automatically after this planning session.

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
