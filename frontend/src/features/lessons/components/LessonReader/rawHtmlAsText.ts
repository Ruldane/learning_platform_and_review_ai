/** Markdown node (mdast) reduced to what this plugin reads and writes. */
interface MdNode {
  type: string;
  value?: string;
  children?: MdNode[];
  data?: { hProperties?: Record<string, unknown> };
}

/** Block parents: an `html` node found there is a raw HTML block, elsewhere it is inline HTML. */
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
 * Remark plugin: a raw HTML block becomes a text paragraph (escaped by React, never
 * interpreted), as in the backend's PDF. An unclosed block (a lone `<pre>`) swallows
 * rest of the lesson: dropping it would make whole sections disappear. Inline HTML stays
 * removed (D89). `skipHtml` keeps what would remain.
 */
export function remarkRawHtmlAsText() {
  return (tree: unknown) => rewrite(tree as MdNode);
}
