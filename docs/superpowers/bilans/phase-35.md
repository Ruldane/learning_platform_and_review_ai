# Phase 35 · Explique-moi

Depuis une leçon publiée ou un fichier enregistré dans l’IDE, l’élève demande une
explication avec un exemple. Le moteur de conversation reprend le tour après
rechargement et pose au plus une relance. Le bilan permet de relire l’échange
et d’accepter jusqu’à trois fiches ainsi qu’une preuve lorsque l’explication est
jugée juste et autonome.

La preuve vise la première compétence du module ou « Développement Python »
pour un fichier Python ou notebook. Elle porte au plus au niveau « En cours »
et conserve un niveau déjà supérieur. Les fiches et la preuve sont enregistrées
en une transaction, dédupliquées lors d’un rejeu. Une modification de la source
pendant l’explication demande de recommencer sur sa nouvelle version. Le fichier
de l’IDE sert de texte de référence.

Le parcours Edge a suivi un projet synthétique, retrouvé la relance après
rechargement, ouvert le bilan puis enregistré les propositions. Les tests
ciblés vérifient aussi le départ depuis une leçon, l’isolation des comptes,
le plafond de preuve et le rejeu de l’acceptation.

À l’intégration, rattacher la migration de la colonne de bilan à la tête
Alembic du lot et reporter le plafonnement de la preuve dans les décisions.
