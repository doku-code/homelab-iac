# 050 — Contrôleur de bootstrap indépendant et doctor read-only

- **Statut proposé :** PLANNED après revue architecture; synthétique en parallèle de100
- **Permission initiale :** OFFLINE_CODE; test sur contrôleur propre séparément autorisé
- **Dépendances :** 030 et code indépendant;040 requis seulement pour test sensible de vraie récupération, pas pour implémentation synthétique

## Objectif

Faire fonctionner les premières vérifications et commandes de bootstrap depuis un contrôleur de confiance **sans** Forgejo, Infisical, runner ni backend distant. Réutiliser les roots et rôles existants, ne pas créer un orchestrateur autonome.

## Portable implementation contract (current)

Deliver verified native tool setup for Mac ARM64 and Linux AMD64, reusing current
Terraform pins, Python requirements and Galaxy requirements. Explicit compatible
Python, checksummed downloads, isolated HOME/collections/cache and exact GitHub
SHA; do not require a Forgejo-only container image or a dedicated VM. Task035
is an optional test adapter, never a dependency for recovering pve-lab itself.

Small Make setup/check/doctor interfaces; default doctor is offline. Synthetic
manifest/state/input fixtures only, no production payload/key access. Check
missing/wrong authority, stale generation, invalid artifact and unavailable
internal endpoints; fail closed, no empty-state fallback or automatic adoption.
Normal Universal Auth workflow stays unchanged; separately reviewed emergency
runtime credential interface must avoid command-line/log/state leakage and
cannot become a second permanent secret store.

Acceptance before production drill: clean Mac/Linux tool matrix or explicit
remaining platform blocker; exact code/tool versions, backend-disabled readonly
validations in code-only workspace, Ansible syntax and synthetic tests with
Forgejo/Infisical/PBS/internal DNS unavailable. Internet dependency explicit;
offline readiness only with a tested complete artifact cache. No Terraform
provider plan or apply in readiness test. Second run cannot change live resources.

Separate approval for clean-machine execution, any optional VM creation and
production recovery material. Cleanup removes only synthetic temporary paths;
keep original authorities. Next040 real capture/retrieval after its own gates;
do not automatically perform it. The older bullets below retain applicable
principles, not a dependency on completing the full kit before coding.

## Travail autorisé

- Documenter versions et installation vérifiable des outils, SSH/trust, accès Proxmox, template/storage/bridge prérequis.
- Créer une commande `doctor` purement observatrice et des préflights qui échouent de façon sûre si le bon state ou une entrée manque.
- Séparer `bootstrap`, `reconcile` et `recover` dans les commandes et la documentation; ne pas faire passer un bootstrap qui arrête un daemon pour une convergence normale.
- Tester sans accès Infisical actif avec des inputs de secours fournis de façon sécurisée et temporaire par l'opérateur; aucun argument CLI contenant un secret.

## Interdit

Aucune adoption automatique de CT, aucun import/state mv/destruction, aucun contournement de host key, aucun bootstrap live non autorisé et aucune intégration des credentials dans le repo.

## Acceptation

Depuis un environnement propre, l'opérateur peut vérifier la version du code, les états/inputs, les artefacts, la confiance et la capacité à atteindre Proxmox sans utiliser le control plane. L'outil dit clairement quand il ne peut pas avancer; la vraie reconstruction reste une tâche/drill distinct.
