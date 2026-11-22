# Phase 15 · Simulateur d’astreinte

Le simulateur avance par gestes sur une horloge fictive. L’alerte active la panne dans le
contexte du scénario et le journal permet de retrouver les symptômes. L’IDE ouvre le projet
de réparation. Le diagnostic rejoue le scénario sur les fichiers sauvegardés du projet. Un
rapport étayé par un événement consulté reste lié à la version qui a passé le diagnostic.
La réparation et le rapport validés ajoutent une preuve de pratique au plus une fois.

La recette Edge a consulté le journal, ouvert Monaco, sauvegardé le service et vérifié les
diagnostics avant et après réparation. La preuve est restée visible après rechargement.
Les modèles du parcours étaient scriptés. Un second contrôle du diagnostic, dans un
conteneur Linux jetable, a validé les trois cas attendus avec le vrai lanceur. Voir D244.
