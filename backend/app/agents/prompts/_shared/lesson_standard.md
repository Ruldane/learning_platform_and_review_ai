## Chapter standard

Introduce one idea at a time, in an order where each step prepares the next. Define each notion
before using it. Briefly recall a notion already covered and refer to the relevant chapter when
the program specifies it. For a new notion, explain its role, its mechanism, the reasons for the
choices and the cases where the approach reaches its limits.

Write code identifiers, comments and messages in English. Write the explanations in the lesson's
language, English by default. Present the code in short steps. Before each block, state the
expected result, then explain how to read what the block produces.

EXACT structure, in this order, with these headings as they are (even in {{ language }}):
{{ title }}
{% for section in sections %}
## {{ section }}
{% endfor %}

Reproduce the level 1 heading as given, removing only the markers that frame the title.

- **Objectifs**. At most three bullets on what January will be able to do at the end.
- **Prérequis**. The notions already introduced, with a recap and the available reference.
- **L'essentiel en 5 lignes**. Exactly five bullets.
- **Explication**. The notions in order with level 3 subheadings. Insert recall questions after
  the important steps. End with a reference sheet that gathers the notions and the decisions to
  remember.
- **Schémas**. At least one Mermaid block of type `flowchart`. Explain what the arrows and the
  nodes represent. Use for example `flowchart TD` then `A["Text"] --> B["Text"]`.
- **Exemple travaillé**. Start from a concrete case and show the reasoning and the result.
- **Erreurs fréquentes**. Give the symptom and the explanation of each error selected.
- **Exercice**. Present the problem, the elements provided and the expected result.
- **Corrigé de l'exercice**. Justify the steps of the solution and explain how to check it.
- **Sources**. Identify the main reference. For each source, give `[n]` and a Markdown link to
  its exact address.
- **Auto-évaluation**. Exactly five numbered questions to recall and apply the notions.
