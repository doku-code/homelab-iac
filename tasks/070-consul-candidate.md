# 070 — Qualification Consul dans un laboratoire isolé

- **Statut :** DEFERRED; optional only if080 establishes a concrete requirement
- **Permission initiale :** OFFLINE_CODE; allocation/test live explicitement autorisés
- **Dépendances :** récupération bootstrap et profil de test indépendant; critères PostgreSQL définis

## Objectif

The mandatory PostgreSQL-versus-Consul sequence is superseded by080. No need
for an additional quorum service has been demonstrated. Preserve this experiment
as an optional future qualification, not a prerequisite to K3s learning, recovery
or PostgreSQL selection. The scope below requires a new explicit assignment.

Comprendre KV, sessions, health checks, service discovery et Raft; évaluer le backend Terraform `consul` sur des preuves équivalentes à PostgreSQL, sans toucher aux states actifs.

## Travail prévu

- Démarrer par une instance jetable confinée; la qualification production exige une configuration ACL/TLS, stockage et sauvegarde réaliste, distincte d'un agent de développement.
- Tester un root Terraform entièrement jetable : CRUD, isolation, vrai locking à deux clients, libération/expiration après panne, consistence et restauration depuis snapshot.
- Mesurer consommation et complexité; documenter contraintes quorum/failure domain pour un éventuel cluster et intérêt réel de service discovery.
- Supprimer les ressources temporaires avec revue de la portée et préserver la preuve des résultats.

## Interdit

Pas de remplacement PostgreSQL, pas de migration d'état existant, pas de public ingress, pas de déploiement sur pve-core critique sans allocation et approbation. Un mode dev PASS n'est pas une qualification production.

## Acceptation

Rapport comparatif équitable et reproductible, gates classifiés; coûts de disponibilité et récupération explicités. Le choix final relève d'une décision séparée et non d'un score inventé par l'agent.
