# 040 — Recovery Kit v1 chiffré et restauration sans écriture

- **Statut proposé :** BLOCKED jusqu'à la tâche 030 et aux choix de garde
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
