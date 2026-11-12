/** Nœud Markdown (mdast) réduit à ce que ce greffon lit et écrit. */
interface MdNode {
  type: string;
  value?: string;
  children?: MdNode[];
  data?: { hProperties?: Record<string, unknown> };
}

/** Parents d'un bloc : un nœud `html` qui y figure est un bloc HTML, ailleurs du HTML en ligne. */
const FLOW_PARENTS = new Set(["root", "listItem", "blockquote", "footnoteDefinition"]);

function textBlock(value: string): MdNode {
  return {
    type: "paragraph",
    data: { hProperties: { className: "whitespace-pre-wrap" } },
    children: [{ type: "text", value }],
  };
}

function rewrite(node: MdNode): void {
  if (!node.children) return;
  const flow = FLOW_PARENTS.has(node.type);
  node.children = node.children.flatMap((child) => {
    if (child.type !== "html") {
      rewrite(child);
      return [child];
    }
    return flow ? [textBlock(child.value ?? "")] : [];
  });
}

/**
 * Greffon remark : un bloc HTML brut devient un paragraphe de texte (échappé par React, jamais
 * interprété), comme le rendu PDF du back. Un bloc ouvert et jamais fermé (`<pre>` seul) avale la
 * suite de la leçon : le jeter ferait disparaître des sections entières. Le HTML en ligne reste
 * retiré (D89). `skipHtml` garde ce qui resterait.
 */
export function remarkRawHtmlAsText() {
  return (tree: unknown) => rewrite(tree as MdNode);
}
