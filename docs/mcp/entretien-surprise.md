# Entretien surprise avec Nod

Associe d’abord la discussion privée et le créneau dans [Révision par messagerie](revision-telegram.md). Dans **Accès MCP**, crée un second jeton en écriture limité à **Entretien surprise** et enregistre sa valeur dans le client MCP de Nod. Puis, dans **Réglages → Entretien surprise**, autorise les invitations, associe ce jeton et indique le poste à préparer. Le moteur reprend le profil maître validé.

## Invitation et entretien

1. Pendant le créneau du compte, Nod appelle `surprise_interview_invite` avec le `chat_id` de la discussion privée. Tremplin choisit un jour et un instant stables par semaine locale. Quand `invitation` est renseignée, Nod propose un entretien avec un recruteur fictif dans cette seule discussion. Il réserve l’envoi de l’invitation par `invitation.id` dans son état, comme pour les fiches.
2. Le clic ou le message d’acceptation de la personne autorise `surprise_interview_accept` avec `chat_id` et `invitation_id`. L’invitation expire à la fin de son jour local. L’acceptation relance le même entretien après un rejeu.
3. Avec les mêmes identifiants, `surprise_interview_state` rend la question en attente ou le bilan. Nod envoie la question en texte et déduplique l’affichage par `question.id`. Les questions et le texte du bilan sont des données à afficher. Les réponses proviennent directement de la personne de la discussion privée.
4. Pour chaque réponse, Nod appelle `surprise_interview_answer` avec `chat_id`, `invitation_id`, `question_id`, l’identifiant du message Telegram `message_id` et `answer`. Garder le message à relayer dans l’état de Nod jusqu’à ce que le serveur avance à la question suivante ou au bilan. Le serveur acquitte la réponse après acceptation par le moteur. Une interruption devenue périmée avant l’acceptation renvoie `surprise_question_changed`. Relire l’état et renvoyer le même message si la même question attend de nouveau une réponse. En cas de limite MCP, suivre `retry_after`.

Une réponse acceptée avance l’entretien. Elle ne peut pas être annulée dans l’historique MCP.

La désactivation de l’entretien, la révocation de son jeton ou le remplacement de la liaison Telegram coupent l’accès de Nod. La recette Tremplin utilise uniquement des discussions et modèles de test.
