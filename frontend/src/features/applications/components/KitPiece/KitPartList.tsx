import { KitPartField } from "./KitPartField";
import type { Part } from "./parts";

interface KitPartListProps {
  parts: Part[];
  pieceTitle: string;
  /** Un enregistrement est en cours : les textes se lisent, ne se changent plus. */
  busy: boolean;
  onChange: (key: string, text: string) => void;
  onCopy: (text: string) => void;
}

/** Les textes d'une pièce : un seul, les deux relances, ou une réponse par question du formulaire. */
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
