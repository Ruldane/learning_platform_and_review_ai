# Tremplin · Routines et vingt nouvelles fonctionnalités

Les dix propositions déjà présentées sont reprises dans les phases 45 à 54.
La phase 44 fournit les routines. Les phases 55 à 63 prolongent les usages
d’apprentissage, de carrière et de transmission.

## Automatisation locale

Une routine appartient à un compte. Elle nomme une action du catalogue et
un déclencheur explicite. L’interface permet d’activer, de suspendre et
d’exécuter une routine. Elle présente l’heure dans le fuseau du compte, le
dernier résultat et les actions qui demandent une décision. Le planificateur
de Tremplin lance les routines activées même en l’absence d’une conversation
Codex. Le premier déclencheur est une heure locale quotidienne. D’autres
actions peuvent ensuite fournir un repère d’événement stable.

Une occurrence a une identité stable et un état durable. Deux passages du
planificateur convergent vers la même exécution. Un redémarrage peut reprendre
un travail réservé selon le résultat déjà enregistré. Le lancement HTTP
répond avec l’identifiant de l’exécution.

## MCP

Chaque nouvelle fonctionnalité expose les lectures utiles au niveau 1 et
des écritures métier aux niveaux 2 ou 3. Les outils d’écriture sont bornés
par compte et par fonctionnalité. La publication, le partage, la modification
d’un planning en vigueur et l’envoi externe passent par les confirmations
existantes. Le catalogue et la garde de couverture MCP vérifient les routes.
La revue des fonctionnalités historiques détaille les actions disponibles et
les exceptions liées aux secrets ou à l’identité.

Les routines passent par les mêmes services métier. Elles peuvent préparer
des brouillons privés et signaler une action à confirmer dans l’application.
Une routine coûteuse affiche son usage et s’active avec un plafond explicite.
Les agents obtiennent leurs modèles via le port existant, configuré sur OpenAI.

## Validation

Un test de comportement ou de régression précède l’implémentation de chaque
phase. Valider une action MCP en lecture et en écriture, l’isolation, un
parcours Playwright sous Edge et la reprise des écritures rejouables.
Les suites de recette utilisent des fournisseurs synthétiques. Les parcours
front, les contrats d’API, les migrations et les couches backend passent
avant le commit du lot.
