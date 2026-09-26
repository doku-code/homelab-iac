# Documentation de `homelab-iac`

> **Point d'entrée documentaire.** Ne pas supprimer ni écraser les runbooks,
> comptes rendus de qualification et historiques existants lors de l'intégration
> de `architecture.md` et `roadmap.md`. Les documents ci-dessous n'ont pas tous
> le même statut : toujours vérifier le code et l'état live avant une action.

## Lire selon le besoin

| Besoin | Référence | Statut |
| --- | --- | --- |
| Comprendre la cible, services, données et bootstrap | [Architecture canonique](architecture.md) | Reconstruction K3s/TrueNAS; exigences approuvées séparées des recommandations |
| Savoir quel milestone vient ensuite | [Roadmap](roadmap.md) et [tâches](../tasks/README.md) | Plan de travail, pas autorisation d'exécuter |
| CI qualité et frontière runner | [CI qualité](ci-quality.md) | Run139 LIVE VERIFIED; clôture sécurité 010/020 distincte |
| Préparer une récupération indépendante | [Contrat et Recovery Kit v1](recovery-contract.md) | Contrat 030 accepté; kit et récupération non qualifiés |
| Préparer capture, garde et validation du kit | [Préparation Recovery Kit](recovery-kit-preparation.md) | Schéma/tests synthétiques; export et drill non exécutés |
| Préparer la VM de test sans GPU | [Contrôleur headless](headless-controller.md) | Adaptateur optionnel035 pour portable050; aucune VM déployée |
| Préparer les trois VM du laboratoire | [Stage A](k3s-stage-a.md) | Implémentation repository-only100; aucune allocation ni VM créée |
| Retrouver les faits établis lors de l'audit | [Audit du 2026-09-24](audits/2026-09-24/executive-summary.md) | Photographie historique, jamais statut live garanti |
| Déploiement et limites du runner CT301 | [Forgejo runner](forgejo-runner.md) | Runbook/état cible; vérifier le service avant intervention |
| Comprendre la sécurité et la migration CI/CD | [Infrastructure CI/CD](infrastructure-cicd.md) | **Contient une proposition S3 historique**; ne pas la suivre comme runbook actif |
| Comprendre les anciennes décisions runner CT300 | [Historique Forgejo runner](forgejo-runner-history.md) | **Historique uniquement**; CT300 est désormais PostgreSQL |
| Comprendre pourquoi Garage n'est pas notre backend | [Évaluation Garage](garage-evaluation.md) | Qualification et décision expérimentale |
| Comprendre le design PostgreSQL | [Design PostgreSQL](terraform-pg-backend-design.md) | Conception initiale; sections historiques si supplantées |
| Consulter les tests PostgreSQL réalisés | [Qualification PostgreSQL](terraform-pg-backend-qualification.md) | Preuves des essais jetables, surtout via SSH |
| Vérifier les gates PostgreSQL les plus récents de ce lot | [Gates PostgreSQL](terraform-pg-production-gates.md) | Checkpoint daté, **pas une autorisation de migration** |
| Sauvegardes PostgreSQL | [Backup PostgreSQL](terraform-pg-backups.md) | Procédure et preuves datées; full PBS restore distinct |
| Incident de démarrage VM502 | [Diagnostic workstation](workstation-start-diagnosis.md) | Diagnostic daté, pas une condition permanente |

## Audit détaillé

Les six documents source restent séparés et **immuables en tant que
photographie du 2026-09-24** : [état actuel](audits/2026-09-24/current-state.md),
[dépendances et bootstrap](audits/2026-09-24/dependency-and-bootstrap.md),
[modularité](audits/2026-09-24/modularity-and-portability.md),
[états et récupération](audits/2026-09-24/state-and-recovery.md) et
[roadmap de l'audit](audits/2026-09-24/milestone-roadmap.md).

La [roadmap canonique](roadmap.md) remplace l'ordre backend/LXC-first par
reconstruction progressive : trois VM headless, K3s, Flux/stateless, stockage
qualifié puis placement et cutovers. Portable recovery avance en parallèle;
le kit complet ne bloque pas l'apprentissage jetable. Les gates CT301 restent
ouverts. Les audits/runbooks conservent leur preuve historique, pas un deuxième
plan actif; vérifier toute divergence avant une opération live.

## Règle de mise à jour

Le [contrat de maintenance](../tasks/README.md#contrat-de-maintenance) définit
quand mettre à jour chaque document, les preuves attendues et les règles de
clôture. Il fait autorité; cet index ne duplique pas les statuts des tâches.

La documentation d'architecture et la roadmap décrivent la situation connue
et la direction cible. Les runbooks conservent les procédures détaillées
vérifiées. Les audits ne sont pas réécrits pour refléter les travaux ultérieurs :
ajouter une nouvelle preuve ou mettre à jour la référence opérationnelle.

Versionner `AGENTS.md` (consignes publiques), mais jamais les states, les secrets, les archives du Recovery
Kit, les plans Terraform sensibles ni les artefacts privés dans ce dépôt public.

La politique de suivi d'AGENTS.md a été explicitement changée après l'audit.
Les mentions historiques « local-only », « untracked » et « never stage » dans
ces six rapports ne sont pas des consignes actuelles. La règle actuelle est
dans [AGENTS.md](../AGENTS.md), désormais versionné.
