# Bilan du lot 4 · Phases 42 et 43

Le mobile ouvre le brief et les fiches préparés sur l’appareil, même après un
rechargement hors ligne. Le serveur rattache la réponse à l’échéance de la
fiche et reconnaît son reçu au retour du réseau. Le changement de compte ou
l’effacement local invalide aussi les écritures en vol.

Le portfolio part d’une sélection vide. L’aperçu et le ZIP restent privés.
L’accord porte la version exacte et l’URL à publier. Un retrait coupe l’accès
suivant. L’utilisateur choisit séparément si l’adresse peut figurer dans les
nouveaux CV ciblés et les futures archives de candidature.

La recette du lot utilise Edge et les doubles locaux. Les réglages d’Agenda
et d’hébergement restent propres à l’installation. Voir les bilans
[mobile](phase-42.md) et [portfolio](phase-43.md).

La revue a vérifié la déconnexion entre onglets, le rejeu d’une approbation
après retrait et les ports par défaut de l’origine publique. L’export du
compte garde les références des fichiers HTML et ZIP. Les liens vers les
sources du portfolio restent utilisables avec la politique de contenu.

La migration SQLite de 0019 à 0052 a conservé 4 programmes et 123 leçons,
avec un contrôle d’intégrité réussi. La pile locale utilise OpenAI pour les
quatre niveaux. Les embeddings mémoire passent par Ollama. Un lot lent
est découpé après expiration du délai de lecture. [D269](../../../DECISIONS.md#d269)

## Après la livraison · Reconstruction des programmes

La reconstruction des quatre programmes avec OpenAI est reportée après la
livraison, conformément à D227. Le pilote LangChain de la phase 11 a coûté
environ 0,25 $ US pour deux chapitres. À ce rythme, 123 leçons coûteraient
environ 15 $ US avant les nouveaux sommaires et les leçons supplémentaires.
Le périmètre et le coût seront recalculés avant la génération de masse.
