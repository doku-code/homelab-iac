# 040 — Recovery Kit v1 chiffré et restauration sans écriture

- **Statut :** BLOCKED — acceptation 030, décisions 040-A à 040-D et autorisation d'export/test
- **Permission initiale :** OFFLINE_CODE; export sensible et transfert demandent une autorisation explicite
- **Dépendances :** contrat validé, emplacement privé ignoré, compte cloud et voie de récupération indépendants, gel des writers

## Objectif

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
| 040-A Code et writers | URL exacte de la copie GitHub, ref/SHA approuvé; vérifier disponibilité/fraîcheur sans Forgejo, compléter par bundle; inventorier et geler tous les writers lors de capture | UNKNOWN : URL indépendante absente de la configuration locale |
| 040-B Garde | Destination chiffrée hors site, compte/MFA récupérables hors homelab, staging privé, format d'encryption authentifiée/recipients, custodian, iCloud + méthode offline séparée, support de copie offline; aucun secret dans la réponse publique | DECISION : rien choisi ou testé ici |
| 040-C Exhaustivité | Autoriser l'inventaire sensible ciblé, préciser sources/versions et copies indépendantes Infisical/Forgejo/TrueNAS/PBS/DNS/OCI; dispositions pour données non régénérables; distinguer copie disponible et test restore manquant | BLOCKED : exports, clés, payloads et layouts non qualifiés; pas d'accès à un dépôt externe sans autorisation |
| 040-D Fraîcheur et essai | Politique de générations/rétention, âge maximal par composant, événements de recapture; contrôleur neuf, réseau isolé, internet ou cache offline, fenêtre et périmètre d'export/transfert/déchiffrement/nettoyage | DECISION : aucun délai/RPO/RTO ou stockage inventé |

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
   vérifier versions/checksums, sept init backend-disabled/readonly + validate
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
en 080-B, après inventaire F1. Aucun backend PostgreSQL/Consul choisi ici.
