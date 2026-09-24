# 050 — Contrôleur de bootstrap indépendant et doctor read-only

- **Statut proposé :** PLANNED après 030–040
- **Permission initiale :** OFFLINE_CODE; test sur contrôleur propre séparément autorisé
- **Dépendances :** Recovery Kit récupérable et accès de secours décidés

## Objectif

Faire fonctionner les premières vérifications et commandes de bootstrap depuis un contrôleur de confiance **sans** Forgejo, Infisical, runner ni backend distant. Réutiliser les roots et rôles existants, ne pas créer un orchestrateur autonome.

## Travail autorisé

- Documenter versions et installation vérifiable des outils, SSH/trust, accès Proxmox, template/storage/bridge prérequis.
- Créer une commande `doctor` purement observatrice et des préflights qui échouent de façon sûre si le bon state ou une entrée manque.
- Séparer `bootstrap`, `reconcile` et `recover` dans les commandes et la documentation; ne pas faire passer un bootstrap qui arrête un daemon pour une convergence normale.
- Tester sans accès Infisical actif avec des inputs de secours fournis de façon sécurisée et temporaire par l'opérateur; aucun argument CLI contenant un secret.

## Interdit

Aucune adoption automatique de CT, aucun import/state mv/destruction, aucun contournement de host key, aucun bootstrap live non autorisé et aucune intégration des credentials dans le repo.

## Acceptation

Depuis un environnement propre, l'opérateur peut vérifier la version du code, les états/inputs, les artefacts, la confiance et la capacité à atteindre Proxmox sans utiliser le control plane. L'outil dit clairement quand il ne peut pas avancer; la vraie reconstruction reste une tâche/drill distinct.
