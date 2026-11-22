# Phase 32 · Pilote de concentration

Le quiz et le training comparent les trois premières réponses évaluées aux trois dernières.
Le pilote se déclenche lorsque la médiane du temps de réponse augmente d’au moins 40 % et
1,5 seconde et que le groupe récent compte deux erreurs supplémentaires. La mesure écarte une
réponse après plus de 30 secondes d’inactivité, un changement d’onglet ou une perte de focus.
Les durées de réponse restent en mémoire dans le navigateur.

Le quiz s’appuie sur les points de sa correction. Une révision plus facile isole une question
et sa correction, puis ramène au résultat. Le training s’appuie sur le repère facultatif du
Tuteur lorsqu’il évalue un exercice. La révision guidée et le bilan partent d’un choix explicite.
La pause conserve le résultat du quiz ou le fil et le brouillon du training.

## Vérifications

Les tests ciblés couvrent l’horloge factice, les deux seuils, la révision du quiz, les repères du
Tuteur et le rejeu du fil. Le parcours Edge utilise la vraie API avec un Tuteur scripté. Il
vérifie l’absence de proposition au démarrage, puis l’acceptation d’une pause et la reprise du
même fil avec son brouillon. La migration locale `0044` a passé l’aller-retour SQLite.
