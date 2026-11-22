# Phase 13 · Pile de lecture

La collecte ajoute des articles, papiers, nouvelles versions et offres du radar. La première
collecte reprend le dernier relevé du radar. Les suivantes reprennent les offres nouvelles.
Les réglages acceptent des sujets, des domaines et des flux RSS ou Atom. Le lecteur présente
le résumé et le texte accessible, le lien de la source et le motif d’arrivée dans la pile.

L’état lu se conserve après rechargement. Depuis une lecture, l’utilisatrice peut la garder
en mémoire, créer une fiche à partir de son résumé, ou proposer un créneau de lecture dans un programme
validé. Une offre peut créer une fiche de candidature avec le contrôle de doublons habituel.
Le brief indique le nombre d’éléments non lus.

Les tests ciblés couvrent le rejeu de la collecte quotidienne, la déduplication de liens,
les filtres, ainsi que l’isolation entre deux comptes pour les sources, les articles et les
actions. La création de fiches est rejouée, l’enregistrement en mémoire et le refus d’une
candidature en double sont vérifiés dans l’API. Les onze routes sont déclarées dans le MCP.

Le parcours Playwright est passé sous Edge à 375 px. Il ouvre un article au clavier, vérifie
le focus sur son titre, change son état et vérifie la mise à jour du compteur. Le navigateur
utilise des réponses de lecture simulées. Le serveur jetable a appliqué la migration `0026`.
