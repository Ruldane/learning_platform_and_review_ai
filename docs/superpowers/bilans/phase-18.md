# Phase 18 · Podcast du matin

Le podcast du matin prend le chapitre du jour, les notes correspondantes, les révisions dues et
les fiches issues des erreurs du quiz de la veille. Le script alterne l’hôte et le coach et
prépare trois questions. Tremplin conserve la transcription avant de produire le son. Le
planificateur réserve un passage par compte et jour local, avec une entrée manuelle sur la page.

La synthèse côté serveur utilise OpenAI Realtime avec deux voix. Le résultat est rangé comme
WAV privé du compte. Le choix de l’API suit la recommandation OpenAI pour une nouvelle
intégration de synthèse. [Guide OpenAI de synthèse vocale](https://developers.openai.com/api/docs/guides/text-to-speech)

Les tests de la recette couvrent l’ordre des segments PCM, les deux voix, le WAV téléchargé,
le repli vers la transcription, le quiz et l’isolation. Le parcours Edge présente la transcription
et corrige les trois réponses quand la piste audio est indisponible. La recette utilise des
fournisseurs simulés.

Un essai distinct avec OpenAI Realtime dans un conteneur jetable a produit une réplique fictive
de 2,85 secondes. Cette mesure vérifie la connexion et le décodage des segments.
