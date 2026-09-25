# 020 — Première CI de qualité sans secrets

- **Statut :** IN_PROGRESS — première exécution live en échec; correction des locks à revérifier dans Forgejo
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

## Première exécution live — 2026-09-24

[Run19](https://git.doku-lab.net/Homelab/homelab-iac/actions/runs/19), commit
`f341450`, a réellement exécuté le job sur CT301 selon l'opérateur; l'API confirme
failure. Checkout/outils réussis, puis échec de validate du root historique
pve-compute-forgejo-runner sur bpg/proxmox0.112.0. Les trois roots précédents
avaient déjà le h1 Linux; ce root, Garage, tfstate et l'exemple ne l'avaient pas.
Les succès locaux macOS antérieurs ne prouvaient donc pas la compatibilité CI.

Cause vérifiée : checksums ZIP officiels présents, mais h1 Linux absent.
Init readonly vérifie le ZIP sans sauvegarder le h1 calculé; validate contrôle
le répertoire décompressé et échoue. Aucun indice de ZIP officiel altéré.
Correction : providers lock pour darwin_arm64 et linux_amd64 depuis le registre
officiel, sans upgrade; ajout d'un seul h1 dans chacun des quatre locks.
Versions, zh et protection readonly conservés. Voir les
[preuves et procédure](../docs/ci-quality.md#provider-lock-portability).

La relance Forgejo du correctif reste NOT TESTED; pas de DONE. L'exécution
opérateur ne vaut pas clôture implicite des questions de sécurité de 010.
Validation correction : les sept init readonly/backend-disabled puis validate
et fmt du workflow passent sur macOS ARM64; les deux packages plateforme sont
vérifiés par providers lock. Linux non exécuté localement (Docker indisponible).
Parsing/syntaxe et guards qualité, liens relatifs et diff --check PASS.
