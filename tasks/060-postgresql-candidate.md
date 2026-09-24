# 060 — Fermer les gates PostgreSQL sans migrer de state

- **Statut proposé :** BLOCKED sur décisions TLS/identités/réseau et prérequis de récupération
- **Permission :** OFFLINE_CODE au départ; LIVE_CHANGE par approbation ciblée
- **Dépendances :** Recovery Kit + contrôleur indépendant pour la reprise, autorisations scoped Cloudflare/Infisical et plan d'accès stable

## Baseline historique

CT300 PG17 a passé CRUD, contention réelle, libération après crash, isolation et restore **via SSH forwarding**. DNS interne, backup logique programmé et restauration de sortie ont été rapportés PASS. Le serveur demeure sur loopback avec un certificat ne correspondant pas au hostname final; production identities, TLS final, egress runner et full PBS restore sont incomplets. Voir les rapports du dossier docs et vérifier le live avant toute action.

## Objectif

Qualifier PostgreSQL comme **candidat** backend self-hosted, sans le déclarer gagnant, l'exposer publiquement ni migrer un state existant.

## Travail prévu par sous-tâches autorisées

- Vérifier la configuration ACME/Cloudflare et obtenir un certificat **dédié** au nom final, renouvelé automatiquement sans dépendre du Mac; secrets diffusés avec le minimum de permissions.
- Établir les adresses de source Mac/runner *réelles*, dont l'egress du job; configurer TLS natif `verify-full`, pg_hba hostssl et restriction réseau.
- Préparer operator/CI identities distinctes et injecter les credentials via Infisical, sans les afficher ni les passer en arguments de processus.
- Qualifier des roots jetables via l'endpoint final : state CRUD, deux vrais clients, lock pendant contention, crash, isolation, refus TLS négatif.
- Tester fraîcheur/alerte de backup et procédure PBS dans une allocation isolée distincte; identifier l'état de chiffrement, sans supprimer les anciens snapshots runner CT300.

## Interdit

Pas de migration, de port WAN, de certificat partagé non autorisé, de credentials dans Git, ni de restore remplaçant CT300. Ne pas modifier CT301, Garage ou d'autres services pour simplifier la qualification.

## Acceptation

Tous les gates approuvés sont marqués PASS sur preuves, ou explicitement BLOCKED/NOT TESTED. La direction Consul reste ouverte. CT300 et son state bootstrap restent récupérables indépendamment du backend.
