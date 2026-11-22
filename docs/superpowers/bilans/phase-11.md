# Phase 11 · Relais, leçons et conversations

## Pilote LangChain

La Fabrique a produit deux chapitres dans un conteneur jetable sur un objectif de test.
L’Éclaireur a lu une sélection de sources officielles LangChain préparée pour la recette.
Le Rédacteur et le Vérificateur ont utilisé OpenAI. L’index et le rendu PDF étaient simulés.

| Chapitre | Mots | Définitions | Profondeur | Exemple | Exercice | Continuité |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [Du texte aux messages LangChain](../recette/phase-11-pilote-langchain/chapitre-01.md) | 2 055 | 92 | 86 | 88 | 82 | 88 |
| [Composer une chaîne de runnables](../recette/phase-11-pilote-langchain/chapitre-02.md) | 1 827 | 96 | 92 | 95 | 94 | 96 |

Chaque chapitre a passé la grille après une révision. Le premier part du texte et définit les
messages, leurs rôles et les modèles de chat. Le second reprend ces notions pour suivre le
passage des données entre deux étapes. Les neuf blocs Python donnent les sorties attendues
avec les types et runnables de `langchain_core` et un modèle simulé. Les numéros cités
correspondent aux sources listées et les deux chapitres contiennent un schéma Mermaid.
Les exemples de composition s’appuient sur les références officielles.
[Messages](https://docs.langchain.com/oss/python/langchain/messages) · [RunnableSequence](https://reference.langchain.com/python/langchain-core/runnables/base/RunnableSequence)

La seconde leçon alterne le tutoiement et le vouvoiement par rapport à la première. Les blocs
de sources contiennent une note sur le traitement des extraits qui peut être supprimée à la
relecture. La reconstruction complète est reportée après la phase 43. La lecture du pilote et
l’accord sur le coût la précéderont à la clôture du projet (D227).

Les 22 appels ont utilisé `gpt-6-luna` et `gpt-6.1-sol`. Tremplin a compté 123 939 jetons d’entrée
et 24 936 de sortie, pour une estimation de 0,250236 $ US. Ce chiffre couvre la Fabrique sur
deux chapitres avec des sources présélectionnées. La reconstruction des plans et le nombre de
chapitres du nouveau sommaire restent à chiffrer.

## Interface

Les sept parcours Playwright de l’application et les deux parcours de connexion et d’isolation
ont passé sous Edge avec des fournisseurs simulés. Le parcours du lecteur simule une réponse
de l’API en cours de vérification et constate le maintien du Markdown et du lien PDF publiés,
puis la mise à jour de la leçon sans rechargement manuel.

## Écritures directes

Le brouillon et sa session de vérification sont enregistrés ensemble. L’ancienne version et
son PDF restent lisibles jusqu’à la publication. L’annulation MCP a été vérifiée avant et
après publication, y compris le rétablissement du PDF précédent, de la mémoire et des
ressources. L’ajout de ressources seul reste immédiat. Les fichiers PDF détachés par une
annulation restent stockés. En cas de panne du rendu pendant une retouche, la Fabrique
réessaie une fois. Si la panne persiste, le chapitre et le PDF précédents restent disponibles.

Les 111 tests ciblés de la Fabrique, du Vérificateur et du garde MCP ont passé. Les tests
démarrés dans une passe groupée qui avaient dépassé les cinq secondes de préparation ASGI
ont passé lors de la relance ciblée. Les 26 tests sur les sessions jouées et la couverture
MCP ont également passé, dont la soumission d’un chapitre à vérifier par Codex.

## Professeur dans la leçon

Le lecteur ouvre un panneau à partir d’un passage sélectionné ou du bouton de conversation.
Le même fil revient à la réouverture. Les réponses en direct deviennent des messages conservés
avec leurs sources. Les liens ouvrent la leçon ou l’élément de mémoire répertorié. La recette
Playwright utilise une réponse simulée pour vérifier l’envoi depuis le clavier, le retour de
focus après Échap et la réouverture avec le fil existant.

Les tests de l’API couvrent le compte propriétaire, le passage répété, les écritures concurrentes,
le rejeu d’un envoi, les budgets et l’annulation MCP. Les plafonds sont contrôlés avant l’appel
avec les comptes de jetons enregistrés par Tremplin. Une interruption peut laisser une
estimation de consommation différente du décompte définitif du fournisseur.

## Migration SQLite

Une copie des fichiers SQLite du transfert est passée de la révision `0019` à `0021` dans un
conteneur hors réseau. `PRAGMA quick_check` a réussi avant et après. Les 4 programmes et les
123 leçons sont présents dans la copie migrée. Le transfert a été monté en lecture seule.
