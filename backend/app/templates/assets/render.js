/*
 * Schémas d'une leçon en SVG (D89). Seul script de la page avec mermaid.min.js (figé, empreinte
 * vérifiée) : le code des blocs <pre class="mermaid"> a été analysé puis réémis par le back
 * (grammaire stricte), il est lu comme texte et rendu en securityLevel "strict". Un schéma en
 * erreur est remplacé par son code. window.__lessonReady passe à true à la fin, quoi qu'il
 * arrive : Gotenberg attend cette valeur (waitForExpression) avant d'imprimer.
 */
(function () {
  "use strict";

  function showCode(block) {
    block.className = "mermaid-source";
  }

  async function renderAll() {
    var blocks = Array.prototype.slice.call(document.querySelectorAll("pre.mermaid"));
    var mermaid = window.mermaid;
    if (!mermaid) {
      blocks.forEach(showCode);
      return;
    }
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "neutral",
      deterministicIds: true,
      suppressErrorRendering: true,
      flowchart: { useMaxWidth: true },
    });
    for (var i = 0; i < blocks.length; i++) {
      var block = blocks[i];
      try {
        var result = await mermaid.render("lesson-diagram-" + i, block.textContent);
        var figure = document.createElement("figure");
        figure.className = "diagram";
        figure.innerHTML = result.svg;
        block.replaceWith(figure);
      } catch (error) {
        showCode(block);
      }
    }
  }

  renderAll()
    .catch(function () {
      Array.prototype.slice.call(document.querySelectorAll("pre.mermaid")).forEach(showCode);
    })
    .then(function () {
      window.__lessonReady = true;
    });
})();
