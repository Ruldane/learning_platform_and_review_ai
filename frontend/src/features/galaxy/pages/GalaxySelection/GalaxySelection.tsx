import { useRef } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Graph, Node } from "../../api";

const paths = {
  lesson: (ref: string) => `/apprendre/lecons/${encodeURIComponent(ref)}`,
  training: (ref: string) => `/etudier/training?${new URLSearchParams({ competence: ref })}`,
  note: (ref: string) => `/memoire?${new URLSearchParams({ item: ref })}`,
};

interface Props {
  node?: Node;
  graph: Graph;
  onSelect: (id: string) => void;
}

function gapText(gap: number) {
  if (gap === 0) return t("galaxy.reached");
  return gap === 1 ? t("galaxy.oneGap") : t("galaxy.gap", { count: gap });
}

export function GalaxySelection({ node, graph, onSelect }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  if (!node) return <p className="text-sm text-muted-foreground">{t("galaxy.choose")}</p>;
  const labels = new Map(graph.nodes.map((star) => [star.id, star.title]));
  const links = graph.edges.filter((edge) => edge.source === node.id || edge.target === node.id);
  const action = node.action;
  return (
    <section aria-labelledby="galaxy-selection" className="flex min-w-0 flex-col items-start gap-2">
      <h2 id="galaxy-selection" ref={heading} tabIndex={-1} className="text-lg font-semibold">
        {t("galaxy.selection")}
      </h2>
      <p className="text-lg font-semibold break-words">{node.title}</p>
      {node.domain && <p className="text-sm">{node.domain}</p>}
      {node.kind === "skill" && <p>{t(`galaxy.levels.${node.level ?? "absent"}`)}</p>}
      {node.gap != null && <p className="font-medium">{gapText(node.gap)}</p>}
      <Link className="underline underline-offset-2" to={paths[action.kind](action.ref)}>
        {t(`galaxy.action.${action.kind}`)}
      </Link>
      {links.length > 0 && (
        <>
          <h3 className="mt-2 font-medium">{t("galaxy.relations")}</h3>
          <ul>
            {links.map((edge) => {
              const peer = edge.source === node.id ? edge.target : edge.source;
              return (
                <li
                  key={`${edge.source}:${edge.target}:${edge.kind}`}
                  className="flex flex-wrap items-center gap-2"
                >
                  <span className="text-sm">{t(`galaxy.relation.${edge.kind}`)}</span>
                  <Button
                    variant="link"
                    onClick={() => {
                      onSelect(peer);
                      heading.current?.focus();
                    }}
                  >
                    {labels.get(peer)}
                  </Button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
