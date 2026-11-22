## Norme du chapitre

Introduis une idée à la fois, dans un ordre où chaque étape prépare la suivante. Définis
chaque notion avant de l'utiliser. Rappelle brièvement une notion déjà vue et renvoie au chapitre
pertinent quand le programme le précise. Pour une notion nouvelle, explique son rôle, son
mécanisme, la raison des choix et les cas où l'approche atteint ses limites.

Écris les identifiants, les commentaires et les messages du code en anglais. Écris les explications dans
la langue de la leçon, le français par défaut. Présente le code par étapes courtes. Avant chaque
bloc, indique le résultat attendu, puis explique comment lire ce que le bloc produit.

Structure EXACTE, dans cet ordre, avec ces titres tels quels (même en {{ language }}) :
# {{ title }}
{% for section in sections %}
## {{ section }}
{% endfor %}

- **Objectifs**. Au plus trois puces sur ce que January saura faire à la fin.
- **Prérequis**. Les notions déjà introduites, avec un rappel et le renvoi disponible.
- **L'essentiel en 5 lignes**. Exactement cinq puces.
- **Explication**. Les notions dans l'ordre avec des sous-titres de niveau 3. Glisse des questions
  de rappel après les étapes importantes. Termine par une fiche de référence qui rassemble les
  notions et les décisions à retenir.
- **Schémas**. Au moins un bloc Mermaid de type `flowchart`. Explique ce que les flèches et les
  nœuds représentent. Utilise par exemple `flowchart TD` puis `A["Texte"] --> B["Texte"]`.
- **Exemple travaillé**. Pars d'un cas concret et montre le raisonnement et le résultat.
- **Erreurs fréquentes**. Donne le symptôme et l'explication de chaque erreur retenue.
- **Exercice**. Présente le problème, les éléments fournis et le résultat attendu.
- **Corrigé de l'exercice**. Justifie les étapes de la solution et explique comment la vérifier.
- **Sources**. Identifie la référence principale. Pour chaque source, indique `[n]` et un lien
  Markdown vers son adresse exacte.
- **Auto-évaluation**. Exactement cinq questions numérotées pour restituer et appliquer les notions.
