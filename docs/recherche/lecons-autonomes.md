# Concevoir des leçons techniques pour Tremplin

Recherche du 19 novembre 2026 sur les exercices en autonomie et le rappel des notions.

## Pratiques documentées

- **Alterner démonstration et pratique.** Le guide de l’Institute of Education Sciences recommande de faire suivre un exemple résolu d’un problème à résoudre. L’aide peut diminuer au fil de la progression. Le même guide recommande de reprendre les notions importantes à distance et de demander une explication du raisonnement. [Guide IES, recommandations 1, 2, 5 et 7](https://www.govinfo.gov/content/pkg/GOVPUB-ED1_600-PURL-LPS117059/pdf/GOVPUB-ED1_600-PURL-LPS117059.pdf)
- **Commencer par lire et expliquer.** PRIMM invite à prédire le résultat d’un code, à le lancer, à expliquer son comportement, puis à le modifier et à créer une variante. L’étude publiée portait sur 493 élèves de 11 à 14 ans. Son application à l’autoformation adulte est ici un choix de conception. [Étude de Sentance, Waite et Kallia](https://eprints.gla.ac.uk/229013/)
- **Faire rappeler la notion de mémoire.** Dans deux expériences sur des textes, un rappel libre a aidé davantage la rétention après deux jours ou une semaine que des relectures répétées. Pour une leçon technique, proposer de reconstruire une règle ou de prédire un résultat avant de rouvrir la leçon. [Étude de Roediger et Karpicke](https://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Roediger-Karpicke-2006_PsychSci.pdf)

## Exemples à reprendre dans Tremplin

| Ressource | Format observé | Application aux leçons |
| --- | --- | --- |
| The Carpentries | En Python, la leçon sur les fonctions fait prédire une sortie, compléter une fonction et réfléchir au cas d’une liste vide. [Conception du cours](https://swcarpentry.github.io/python-novice-gapminder/design.html) | Après une démonstration courte, faire modifier une règle et vérifier un cas limite. |
| MDN | Les exercices ciblent une notion. Les défis plus espacés combinent plusieurs notions. L’exercice sur les fonctions fournit du code de départ et une solution à ouvrir. [Guide des exercices MDN](https://developer.mozilla.org/en-US/docs/Learn_web_development), [exercice sur les fonctions](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/Test_your_skills/Functions) | Prévoir un exercice par leçon, puis un défi qui réutilise plusieurs notions du module. |
| Exercism | L’énoncé précise ce que le code doit faire. Le code de départ, les indices et les tests de l’exercice ont chacun leur place. [Guide de conception d’Exercism](https://exercism.org/docs/building/tracks/concept-exercises) | Donner un résultat vérifiable et un premier indice qui débloque le raisonnement. |
| CS50P | Le problème fournit des entrées et des sorties attendues pour le test manuel, ainsi qu’une commande de vérification. [Exercice Math Interpreter](https://cs50.harvard.edu/python/psets/1/interpreter/) | Donner au moins un cas nominal et un cas limite reproductibles. |

## Format retenu pour une leçon

1. Ouvrir avec un objectif observable et les prérequis nécessaires.
2. Montrer un exemple assez court pour en prédire le résultat, puis expliquer le raisonnement.
3. Proposer une variante à réaliser avec des données de départ, des résultats attendus et des indices avant la correction.
4. Placer la correction dans sa propre section Markdown et expliquer le piège le plus probable. Le lecteur Tremplin affiche le HTML brut comme du texte, ce qui exclut une correction repliable en HTML. [Rendu du lecteur Tremplin](../../frontend/src/features/lessons/components/LessonReader/rawHtmlAsText.ts)
5. Clore par des questions auxquelles répondre de mémoire. Reprendre une notion précédente dans une leçon ultérieure et utiliser les fiches pour les rappels espacés. [Plan d’étude de Tremplin](../superpowers/plans/2026-11-12-06-phase-5-etude.md)
