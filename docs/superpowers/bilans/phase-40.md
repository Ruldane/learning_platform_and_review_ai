# Phase 40 · Mode vocal

Dans le Tuteur et l’entretien, l’utilisatrice choisit de démarrer
l’enregistrement. Le navigateur demande alors l’accès au micro et libère les
pistes à l’arrêt ou à l’annulation. Un second geste envoie le clip à OpenAI pour
la transcription. Le résultat complète le brouillon, qui reste modifiable
jusqu’à l’envoi depuis le formulaire habituel. La saisie reste accessible
pendant une demande audio et en cas de refus ou d’échec.

Le clip est encodé en WAV PCM mono 16 kHz. Le serveur valide ses octets et
borne la durée à 60 secondes et le corps à 2 Mio. Les routes utilisent la clé
OpenAI du compte à travers le port de réglages. Tremplin ne conserve
durablement ni les clips ni les brouillons vocaux abandonnés. Une déconnexion
annule la requête au fournisseur. [Transcription de fichiers OpenAI](https://developers.openai.com/api/docs/guides/speech-to-text)

La restitution se déclenche aussi sur demande et reprend le port de synthèse
du podcast. Le texte reste affiché à côté du lecteur. Une lecture porte au
plus sur les 1 200 premiers caractères, avec un libellé de prévisualisation
pour les textes longs.

- Dans P35, l’option `voice` d’`InterruptCard` branche le brouillon vocal et
  la lecture sur le champ unique des explications.
- Dans P39, `VoiceDraftControls` remplit la soutenance avec `mergeVoiceDraft`
  et `VoicePlayback` lit la consigne. La remise du tableau et du texte suit
  le parcours existant.

La recette Edge a demandé la lecture d’une question, puis enregistré un clip
depuis le micro simulé. L’utilisatrice de test a corrigé la transcription
avant de remettre la réponse et le débrief a affiché les notes de clarté et
de structure. Les fournisseurs vocaux et l’Intervieweur étaient factices.
