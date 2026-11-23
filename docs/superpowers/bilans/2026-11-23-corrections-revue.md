# Bilan des corrections de la revue

Le lot corrige les huit constats de la revue de `802f367` sur la branche
`codex/reorganisation`.

## Effacement du compte

Le formulaire repart de zéro au changement de compte. Son identité attendue
est vérifiée par le serveur. L’effacement demandé par MCP reste associé au
compte du jeton et nécessite une confirmation.

La migration `0073` ajoute le suivi des purges pour les comptes Google effacés.
Un HTTP 202 indique une purge vectorielle qui reprendra en arrière-plan.
Le travail est associé à l’ancien identifiant du compte et disparaît après le
succès de la purge. Il est repris par le planificateur au démarrage puis
toutes les dix minutes. Un espace local conserve son identifiant et reçoit un
message explicite si la purge doit être lancée à nouveau.

## Validation, CV et MCP

Les réponses 422 utilisent les chemins et les messages autorisés par le
serveur. Le CV ciblé vérifie l’association des chiffres aux mesures, à la
validation et à la composition du PDF. Les corrections ambiguës passent par
une confirmation et peuvent être appuyées par le profil maître.

Le journal MCP utilise les identifiants cités par une réponse réussie ou
attribués par le serveur. Les anciennes entrées expirent selon la durée
habituelle de 30 jours. Terminer ou abandonner une séance guidée par MCP
passe au niveau 3.

## Interface

La recherche de conversations ignore la casse et les accents dans tous les
clients. Le fil ouvert et son brouillon gardent leur place pendant la
recherche. Le Labo indique le prérequis audio OpenAI du Podcast d’après la
même source que `tremplin_overview`.

## Recette

- Edge a validé sept parcours sur des piles de test, dont les deux comptes
  Google factices, le changement de compte avant effacement, le CV jusqu’au
  PDF, les conversations et le Labo. La migration de la base de recette
  atteint la révision `0073`.
- Les tests ciblés vérifient aussi la reprise de purge lorsque l’index est
  indisponible, le cloisonnement entre comptes, les erreurs 422, la
  confirmation de séances et le contenu du journal MCP.
- Les décisions D300 à D304 sont dans [DECISIONS.md](../../../DECISIONS.md#d300).
