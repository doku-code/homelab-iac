# 090 — Premier module LXC réutilisable et deuxième profil

- **Statut proposé :** PLANNED
- **Permission initiale :** OFFLINE_CODE; déploiement jetable séparément autorisé
- **Dépendances :** CI qualité fonctionnelle, contrat states validé et roots actuels inventoriés

## Objectif

Extraire une seule responsabilité répétée des roots CT propres au monorepo et prouver qu'elle fonctionne sur un deuxième profil Proxmox compatible. Ne pas commencer par les workstations GPU.

## Travail prévu

- Comparer les CT récentes (PG, Garage, runner), identifier un contrat minimal sans imposer leurs paramètres applicatifs.
- Définir les variables node, storage, template, réseau, sizing, ssh/trust et outputs; les paramètres spécifiques à `doku-lab` restent dans les roots/environnements.
- Préparer les éventuels blocs `moved`/changements d'adresses dans une **tâche explicitement approuvée**, jamais en même temps qu'une migration de backend.
- Valider des profils différents avec des tests synthétiques, puis sur ressources jetables approuvées; vérifier l'idempotence/no-op et les conditions d'échec de préflight.

## Interdit

Pas de refactor général des sept roots, de scheduler implicite, de migration de state, de changement de GPU/USB ou d'extraction immédiate vers un dépôt distinct.

## Acceptation

Le même module est utilisé par deux profils sans modifier son code, les plans des roots existants n'entraînent pas de remplacement non voulu, les prérequis matériels sont explicites et un autre utilisateur peut suivre un exemple public non sensible.
