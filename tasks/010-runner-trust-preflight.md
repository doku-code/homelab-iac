# 010 — Gate de sécurité CT301 avant CI de qualité élargie

- **Statut :** BLOCKED — sources des connexions partagées et acceptation opérateur à confirmer
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

## Résultat hors ligne — 2026-09-24

[Frontière CI et preuves](../docs/ci-quality.md) : plus de trigger PR; main
uniquement avec gate d'activation. Aucun changement live runner ou Forgejo.
Le socket global et l'accès LAN restent des risques; droits de contribution,
protections de branche, token et paramètres Actions sont UNKNOWN.
Prochaine action : revue opérateur et vérifications read-only ciblées autorisées,
ou choix d'un runner isolé. Ne pas activer ni pousser avant cette revue.
La tâche 020 avance seulement sur l'alternative hors ligne autorisée.

## Préflight read-only initial — 2026-09-24

Observation antérieure à la publication confirmée ci-dessous; ne décrit plus
le workflow actuellement publié.

Inspection autorisée après le commit documentaire `510d8f1`. Aucun secret affiché,
job lancé, push, activation ou changement de configuration. **BLOCKED**, pas DONE.

| Vérification | Preuve et limite |
| --- | --- |
| Service CT301 | Active/running; runner v13.0.0, utilisateur runner, groupe podman |
| Hardening systemd | NoNewPrivileges=yes, PrivateTmp=yes, ProtectSystem=strict; ne retire pas l'autorité du socket |
| Runtime | Podman5.4.2 rootless=false; socket root:podman0660, répertoire0710 |
| Configuration effective | privileged=false, options vides, docker_host="-", valid_volumes autorise globalement le socket rootful |
| Connexions | Trois URL racine; homelab-iac/forgejo-theme sur ci-base:1.0.0, cem sur cem-ci:1.0.3 |
| Secrets stockés | Config/registry auth runner:runner0600; valeurs non affichées |
| Réseau | Bridge podman internal=false, route CT vers LAN; isolation/egress d'un vrai job NOT TESTED |
| Jobs | Aucun conteneur actif observé; aucun job ni test de mount lancé |
| Forgejo | Version16.0.4; dépôt public, Actions activé, main par défaut |
| Protection main | API branche retourne protected=false |
| Workflow publié main | push/pull_request sans gate; aea08e2 n'est PAS encore publié |
| Accès anonyme | pull=true, push/admin=false; ne prouve pas les droits des collaborateurs |
| APIs protégées | Collaborateurs, règles détaillées et variable CI_QUALITY_APPROVED : HTTP401, restent UNKNOWN |

Chaîne : événement publié -> label homelab-iac -> daemon partagé -> conteneur
Podman rootful. Le workflow local ne demande pas de socket, mais un auteur de
workflow peut demander le volume globalement autorisé. Le hardening systemd du
daemon n'isole pas l'API du moteur rootful. Aucun exploit ni accès à un autre
dépôt testé. État actif ne prouve pas exécution sûre du nouveau pipeline.

## Publication et contrôle ciblé — 2026-09-24

Ce checkpoint remplace les conclusions précédentes sur le workflow publié.
L'opérateur confirme être le seul autorisé à pousser dans homelab-iac; cette
attestation ne porte pas sur les autres sources du daemon partagé.

- API du fichier main : `510d8f1`, push main + workflow_dispatch seulement,
  condition main ET `vars.CI_QUALITY_APPROVED == 'true'`. Pas de trigger PR.
- [Run17](https://git.doku-lab.net/Homelab/homelab-iac/actions/runs/17) : ID API128,
  push de `510d8f1a8e7d7ada71c44a04cb236bd901c10c0a`, event_payload.ref
  `refs/heads/main`, need_approval=false, job validate skipped, runner_id=null.
  La condition main est vraie : c'est donc l'égalité de la variable qui n'a
  pas été satisfaite. HTTP401 sur la variable interdit de conclure absent vs
  autre valeur. Le warning permissions n'est pas la cause du skip.
- `permissions: contents: read` retiré car ignoré par Forgejo (warning opérateur).
  Aucune restriction équivalente du token n'est établie; test local ajusté pour
  empêcher le retour de cette déclaration trompeuse au niveau workflow/job.
- CT301 toujours active : daemon utilisateur runner, groupe podman; image
  ci-base:1.0.0 sans User explicite, donc job root dans le conteneur. Cela ne
  signifie pas automatiquement root du CT sans socket/évasion.
- Config effective : privileged=false, options vides, docker_host="-"; aucun
  envs/env_file de job observé. Aucun volume déclaré dans l'image; aucune entrée
  active dans mounts.conf système/utilisateur ni override de volumes dans les
  containers.conf inspectés. Aucun montage de socket demandé par validate.yml.
- Aucun nom d'environnement correspondant à TOKEN/SECRET/PASSWORD/PROXMOX/
  INFISICAL/AWS_/PGPASSWORD observé dans l'image ou le processus daemon. Ce
  contrôle de noms n'est PAS une preuve exhaustive d'absence de secrets dans
  les couches image. Aucune valeur secrète affichée. Workflow sans secrets.*;
  auth checkout temporaire et auth registre côté daemon restent nécessaires.
- Config et auth registre sur hôte protégées0600, sans montage déclaré dans
  ce job. Le socket globalement autorisé permet toutefois à un autre workflow
  de demander l'autorité rootful et d'accéder aux ressources du CT.
- Trois connexions effectives : homelab-iac/forgejo-theme -> ci-base:1.0.0;
  cem -> cem-ci:1.0.3. Scopes déclarés : dépôt homelab-iac, organisation CEM,
  dépôt thème. Les URLs racine ne prouvent pas les scopes d'enregistrement.
  API runners HTTP401 : scopes et auteurs admis côté serveur non vérifiés.
- Bridge non interne et route LAN observés : pas de preuve d'egress restreint;
  aucun test réseau depuis un job effectué. Cet accès est inutile aux checks
  d'infrastructure hors ligne mais demeure un risque partagé.

### Acceptation et prochaine action

- PASS : chaîne du job revu et limites documentées; état actif distinct d'un
  résultat CI. Aucun job lancé ni configuration live modifiée.
- BLOCKED : inventaire authentifié des sources admises/token et acceptation
  explicite du périmètre partagé. Pas de DONE ni de LIVE VERIFIED.
- Alternative immédiate sûre : continuer les validations locales existantes.
  La première exécution réussie sera une preuve Q2/020, pas supposée ici.
- Validation du correctif : scripts/check-quality.py PASS (51 YAML, 6 Python,
  18 scripts/blocs shell, assertions triggers/gate); 8 cibles de liens relatifs
  PASS; git diff --check PASS. Diff staged revu. Les validations Terraform et
  Ansible complètes antérieures ne sont pas présentées comme rejouées ici.

L'opérateur doit confirmer dans l'administration Forgejo les scopes des trois
connexions, les auteurs/événements admis (aucun code non fiable), les capacités
du token et accepter explicitement socket partagé/LAN pour le commit main revu.
Aucun accès à un autre dépôt n'a été effectué. Si des sources non fiables sont
admises, demander une correction ciblée de leurs droits avant activation, pas
automatiquement un second runner. Aucune protection de branche n'est inventée
pour compenser main protected=false; risque accepté ou correction séparée.

La procédure exacte de variable puis dispatch, après cette approbation et
publication du correctif, est dans [CI quality](../docs/ci-quality.md#next-security-action).
Pas d'apply, de changement de credentials, de state ou d'audit historique.
