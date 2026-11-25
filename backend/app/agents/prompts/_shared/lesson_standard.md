## Chapter standard

Introduce one idea at a time, in an order where each step prepares the next. Define each notion
before using it. Briefly recall a notion already covered and refer to the relevant chapter when
the program specifies it. For a new notion, explain its role, its mechanism, the reasons for the
choices and the cases where the approach reaches its limits.

Write code identifiers, comments and messages in English. Write the explanations in the lesson's
language, English by default. Present the code in short steps. Before each block, state the
expected result, then explain how to read what the block produces.

Use the headings below in this exact order. Keep the headings in English in a {{ language }} lesson.
{{ title }}
{% for section in sections %}
## {{ section }}
{% endfor %}

Reproduce the level 1 heading as given, removing only the markers that frame the title.

- **Objectives**. At most three bullets on what January will be able to do at the end.
- **Prerequisites**. The notions already introduced, with a recap and the available reference.
- **Key points in 5 lines**. Exactly five bullets.
- **Explanation**. The notions in order with level 3 subheadings. Insert recall questions after
  the important steps. End with a reference sheet that gathers the notions and the decisions to
  remember.
- **Diagrams**. At least one Mermaid block of type `flowchart`. Explain what the arrows and the
  nodes represent. Use for example `flowchart TD` then `A["Text"] --> B["Text"]`.
- **Worked example**. Start from a concrete case and show the reasoning and the result.
- **Common mistakes**. Give the symptom and the explanation of each error selected.
- **Exercise**. Present the problem, the elements provided and the expected result.
- **Solution**. Justify the steps of the solution and explain how to check it.
- **Sources**. Identify the main reference. For each source, give `[n]` and a Markdown link to
  its exact address.
- **Self-assessment**. Exactly five numbered questions to recall and apply the notions.
