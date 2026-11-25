import { KitPartField } from "./KitPartField";
import type { Part } from "./parts";

interface KitPartListProps {
  parts: Part[];
  pieceTitle: string;
  /** A save is in progress: the texts are read-only now. */
  busy: boolean;
  onChange: (key: string, text: string) => void;
  onCopy: (text: string) => void;
}

/** The texts of a piece: a single one, the two follow-ups, or one answer per form question. */
export function KitPartList({ parts, pieceTitle, busy, onChange, onCopy }: KitPartListProps) {
  return (
    <div className="flex flex-col gap-3">
      {parts.map((part) => (
        <KitPartField
          key={part.key}
          part={part}
          pieceTitle={pieceTitle}
          busy={busy}
          onChange={(text) => onChange(part.key, text)}
          onCopy={() => onCopy(part.text)}
        />
      ))}
    </div>
  );
}
