# 020 — Première CI de qualité sans secrets

- **Statut :** BLOCKED pour exécution live; code local validé, en attente de revue
- **Permission initiale :** OFFLINE_CODE; exécution de jobs uniquement sur refs approuvées
- **Dépendances :** frontière de confiance CT301 documentée et approuvée

## Objectif

Obtenir rapidement un pipeline Forgejo qui valide le dépôt automatiquement **sans backend réel, state de production, credential Infisical/Proxmox, socket privilégié, `plan` live ni `apply`**. Renforcer le workflow existant au lieu de le remplacer entièrement.

## Étapes de livraison

1. Minimal : format Terraform, validate des roots prévus avec backend désactivé et providers de version vérifiée; syntaxe Ansible; parsing YAML; tests synthétiques runner; tests backup hors ligne; contrôle de whitespace.
2. Couverture : six stacks dont le root historique, treize playbooks, vingt cas runner et deux tests backup. Le root d'exemple exige une installation vérifiée du provider; le workflow utilise désormais init backend-disabled avec lockfile readonly pour les sept roots.
3. Hygiène : exécuter réellement le scanner de secrets, avec binaire/action pinné et téléchargement vérifié. Vérifier les artefacts générés et logs; aucun dump/state/plan ne doit être publié.
4. Sujets séparés : corriger le couplage `node_exporter`→monitoring Compose, inspecter les comportements Make divergents et pinning/checksum dans des commits indépendants après validation ciblée.

## Interdit

Ne pas utiliser par défaut les wrappers Make qui injectent Infisical. Ne pas monter le socket Podman dans un job de validation. Ne pas autoriser des PR non fiables sur le runner partagé avant preuve d'isolation. Pas de création de guest, d'Ansible convergence, de Terraform state/plan de production, d'identité CI élevée ou de push automatique.

## Acceptation

- Un changement de référence autorisée déclenche un workflow et produit un statut clair.
- Tests pertinents répétables et mêmes versions des outils connues; les six stacks et treize playbooks ont un verdict précis.
- Le scanner de secrets est effectivement exécuté, sans imprimer le secret détecté dans le rapport.
- Aucun credential/state de production ni permission destructive n'est disponible pour la CI qualité.
- La future CD reste un workflow/tâche distinct nécessitant des autorisations ultérieures.

## Livraison locale — 2026-09-24

Workflow existant renforcé sans nouveau framework : gate main/variable,
checksums Terraform/Gitleaks, sept roots isolés, tests backup, parsing/syntaxe,
whitespace et scan d'historique sans publication des findings.
Voir [commandes et limites](../docs/ci-quality.md). Aucun run Forgejo, push ou
activation. Le gate 010 reste ouvert : pas de DONE ou LIVE VERIFIED.
Le correctif exporter/Compose et les refactors Make sont différés.
