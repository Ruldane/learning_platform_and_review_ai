import { SourceCard } from "../SourceCard";
import type { SourceView } from "../sourceTypes";
import { SourcesBlock } from "./SourcesBlock";

/** Un bloc de sources : une carte par page. */
export function SourceList({ title, sources }: { title: string; sources: SourceView[] }) {
  return (
    <SourcesBlock title={title} count={sources.length}>
      <ul className="flex flex-col gap-2">
        {sources.map((source) => (
          <li key={source.id}>
            <SourceCard source={source} />
          </li>
        ))}
      </ul>
    </SourcesBlock>
  );
}
