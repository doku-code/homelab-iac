# 010 — Gate de sécurité CT301 avant CI de qualité élargie

- **Statut proposé :** READY après 000
- **Permission initiale :** READ_ONLY + OFFLINE_CODE
- **Dépendances :** baseline intégrée; accès de vérification existants autorisés

## Contexte

L'audit constate que CT301 exécute Forgejo Runner et que l'accès au socket Podman rootful est équivalent à un privilège élevé dans le CT. `valid_volumes` autorise le socket; une convention « publication seulement » n'est pas un contrôle technique par connexion. Un job sans secrets peut néanmoins exécuter du code nuisible s'il accède à un runner privilégié ou au réseau interne.

## Objectif

Établir précisément **quelles références Git, quels workflows et quels utilisateurs peuvent exécuter du code** sur le runner, quels mounts/socket et quel réseau deviennent accessibles au job, et quels labels utilisent réellement les images approuvées. Livrer le périmètre sûr de la tâche 020.

## Travail autorisé

- Audit des triggers actuels, du modèle de confiance Forgejo et des droits de contribution/édition des workflows.
- Inspecter de manière sûre la configuration runner/Podman effective et la santé du runner sans modifier son enregistrement ni exposer les tokens.
- Proposer de petites protections testables; n'appliquer que les changements de code hors ligne autorisés. Toute modification active du runner demande une autorisation séparée.
- Établir une liste explicite des refs autorisées et la politique des forks/PR non fiables.

## Interdit

Aucun job non fiable sur le runner partagé, aucun montage du socket dans la CI de validation, aucune exposition des credentials, aucun changement de permissions rootful « pour que ça marche », aucune suppression des anciennes images à titre cosmétique.

## Acceptation

- La chaîne « événement Git → job → runtime → socket/réseau/secrets » est documentée à partir de preuves.
- La CI de qualité dispose d'un périmètre de confiance approuvé ou reste `BLOCKED` avec une alternative sûre.
- Les vérifications du service runner distinguent « actif » de « capable d'exécuter un job »; pas de faux PASS.
