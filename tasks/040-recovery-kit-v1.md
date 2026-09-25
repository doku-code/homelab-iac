# 040 — Recovery Kit v1 chiffré et restauration sans écriture

- **Statut :** ADAPTED / BLOCKED pour production; préparation synthétique implémentée
- **Permission initiale :** OFFLINE_CODE; export sensible et transfert demandent une autorisation explicite
- **Dépendances :** 030 accepté; portable050 pour essai indépendant (035 facultatif); staging non synchronisé, garde indépendante, inventaire complet et gel des writers avant capture

## Objectif

Reconstruction target revision 2026-09-25: this production recovery track is
NOT a prerequisite for disposable100/110/120. Separate synthetic portable tests
from sensitive capture. Extend required inventory deliberately when new states
exist; preserve the existing six-root verifier/evidence until that code task.
K3s technical recovery must include snapshot plus matching server token if
cluster identity is preserved, or an explicit clean-rebuild/service-restore
contract. Bulk user bytes remain in separate backup policy. Architecture and
roadmap supersede the earlier backend-first ordering; 140 owns production DR.
Observed preparation CI run25/c636d1f passed, not a kit recovery test.

Créer une génération datée **chiffrée avant envoi** contenant le minimum nécessaire au bootstrap, puis prouver qu'elle est récupérable sur un autre contrôleur de confiance. Le cloud est un transport de copies scellées, jamais un backend Terraform.

## Travail autorisé après approbation

- Construire un exporter ciblé qui n'ingère pas « tout le dépôt »; manifeste versionné de façon privée et lié à un commit Git identifié.
- Ne remettre aux machines de sauvegarde que la capacité de chiffrer, pas systématiquement la clé privée de déchiffrement.
- Conserver la clé de récupération via le trousseau iCloud **et** une méthode hors ligne, en incluant la récupération du compte/2FA sans appareil principal.
- Produire une génération, vérifier son checksum et sa présence hors site, puis la récupérer et la déchiffrer sur un deuxième contrôleur dans un dossier isolé.
- Vérifier structure/lineage des states **sans commande fournisseur écrivant**, et conserver un rapport public expurgé.

## Interdit

Ne pas mettre states, dump, clés ou archives dans Git, dans les journaux ou dans les tâches publiques; pas de synchronisation directe du state actif; pas d'apply ni d'import au moment du test. Ne pas remplacer silencieusement une génération précédente prouvée récupérable.

## Acceptation

Une autre machine retrouve la version de code associée, l'archive et les moyens de déchiffrement indépendants; toutes les sommes de contrôle correspondent, les inputs de bootstrap sont inventoriés et aucune deuxième autorité Terraform n'est créée. Les limites du test (pas de restauration Proxmox réelle) sont explicites.

## Spécification et décisions ciblées

Suivre le [contrat et manifeste](../docs/recovery-contract.md), sans exporter
quoi que ce soit avant approbation. Ces sous-tâches sont le prochain travail
040, pas de nouveaux systèmes de gestion ni une autorisation implicite.

| ID | Décision / preuve à fournir par l'opérateur | Gate |
| --- | --- | --- |
| 040-A Code et writers | GitHub doku-code/homelab-iac approuvé, SHA indépendant initial 0ccbccb vérifié; six authorities structurellement recontrôlées | Bundle et gel non exécutés; autres writers à attester avant capture |
| 040-B Garde | iCloud Drive ciphertext approuvé; récupération Apple existante + iPhone de secours confirmés; age proposé, staging hors checkout/sync | Recipient, custodian/support offline et récupération non testés; aucune clé manipulée |
| 040-C Exhaustivité | Inventaire read-only autorisé; PBS/DNS/OCI vérifiés par métadonnées ciblées | Accès Infisical/TrueNAS indisponible; layouts Forgejo/DB et copies indépendantes non qualifiés; aucun export |
| 040-D Fraîcheur et essai | Politique proposée dans préparation; VM headless 035 validée par CI | Âges/rétention à approuver après mesure; allocation/plan/apply/start/drill non autorisés |

Preuves, schéma privé v1, plan d'export ciblé et limites du validateur :
[préparation du kit](../docs/recovery-kit-preparation.md). `make recovery-check`
valide des fixtures synthétiques uniquement. Aucun kit produit ni récupéré;
un PASS structurel ne satisfait pas les gates de qualification ci-dessous.

Validation locale 2026-09-25 : dix tests synthétiques PASS; parsing/guards
52 YAML, 9 Python et 20 scripts/blocs shell PASS; 82 liens/ancres Markdown
et blocs vérifiés; diff/staged whitespace PASS. Ignores privés vérifiés.
Le verdict Forgejo du commit de préparation doit être observé après push,
indépendamment du succès 035; aucun succès de récupération n'est revendiqué.

## Gates de qualification de 040

1. **Préparation :** décisions signées/acceptées, source SHA récupérée par la voie
   indépendante, staging privé protégé, scope d'export explicite; aucun state/
   secret suivi par Git. Noter les preuves de gel des writers, sans contenu privé.
2. **Capture :** manifeste complet, cohérence inputs/states/code et snapshots de
   service; six states identifiés (historique distinct), versions/trust/inputs
   listés, chaque payload requis présent ou récupérable indépendamment. Manquant
   = FAIL/BLOCKED, pas simple avertissement suivi d'un kit déclaré complet.
3. **Protection :** chiffrement authentifié avant transfert, recipients vérifiés,
   sommes/tailles correctes; altération et clé incorrecte échouent. Ne pas écraser
   la dernière génération prouvée. Receipt indépendant et facteurs hors archive.
4. **Perte du contrôleur :** depuis une autre machine de confiance sans anciens
   caches/sessions, récupérer ciphertext + code et déchiffrer sans Forgejo,
   Infisical, PBS, backend, DNS/SSO internes ni appareil principal. Tester aussi
   la voie offline de clé/copie; documenter dépendance internet externe si choisie.
5. **Intégrité :** vérifier tous les fichiers/références, SHA, outils, ressources/
   lineage/serial privés et chemins; tester rejet d'un fichier absent/corrompu
   et d'un mauvais root. Aucun log sensible, upload public ou deuxième state actif.
6. **Contrôleur neuf :** reconstruire .venv et collections depuis les dépendances,
   vérifier versions/checksums, huit init backend-disabled/readonly + validate
   dans une copie de CODE séparée des states récupérés, syntaxe Ansible avec
   inventaire statique et tests offline. Aucun wrapper Infisical, provider auth,
   plan, apply, import ou convergence. Consigner accès internes bloqués pendant
   l'essai; les états récupérés restent read-only/recovery-only.
7. **Rapport et hand-back :** preuves privées de récupération et rapport public
   expurgé, génération/commit/outils/checks/limites; nettoyer les déchiffrements
   temporaires selon la garde approuvée, maintenir originals et writer unique.
   Le test ne désigne pas automatiquement un nouveau writer et n'autorise pas
   de restore service. Tous les gates PASS + acceptation opérateur avant DONE.

Ce test qualifie la disponibilité du kit et le bootstrap statique du contrôleur,
pas la récupération applicative. L'interface de secours et la vérification
read-only de Proxmox restent 050; restaurations isolées de fondations/services
en 140-C, après inventaire ciblé et sauvegardes indépendantes. Aucun backend choisi ici.
