import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { MAX_CONTENT, type Part } from "./parts";

interface KitPartFieldProps {
  part: Part;
  /** Le nom de la pièce : celui du texte quand il n'a pas de nom propre. */
  pieceTitle: string;
  /** Un enregistrement est en cours : le texte se lit, ne se change plus. */
  busy: boolean;
  onChange: (text: string) => void;
  onCopy: () => void;
}

/** « À remplir par toi » ou « À compléter » tant que la réponse laissée par le code est vide. */
function blankMarker(part: Part): string | null {
  if (!part.blank || part.text !== "") return null;
  return t(
    part.blank === "salary"
      ? "applications.kitPiece.blankSalary"
      : "applications.kitPiece.blankComplete",
  );
}

const rowsOf = (text: string) => Math.min(18, Math.max(4, text.split("\n").length + 1));

/** Un texte de la pièce : modifiable, copiable ; une réponse laissée par le code est marquée. */
export function KitPartField({ part, pieceTitle, busy, onChange, onCopy }: KitPartFieldProps) {
  const id = useId();
  const name = part.label ?? pieceTitle;
  const marker = blankMarker(part);
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      {part.label ? (
        <label htmlFor={id} className="text-sm font-medium">
          {part.label}
        </label>
      ) : null}
      {marker ? (
        <span
          id={`${id}-blank`}
          className="w-fit rounded-md border-2 border-foreground/40 px-2 py-0.5 text-xs font-medium"
        >
          {marker}
        </span>
      ) : null}
      <textarea
        id={id}
        aria-label={part.label ? undefined : t("applications.kitPiece.field", { name })}
        aria-describedby={marker ? `${id}-blank` : undefined}
        value={part.text}
        data-part={part.key}
        maxLength={MAX_CONTENT}
        rows={rowsOf(part.text)}
        readOnly={busy}
        onChange={(event) => onChange(event.target.value)}
        className={cn(fieldClass, "h-auto py-2 font-sans leading-relaxed")}
      />
      <div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={part.text.trim() === ""}
          aria-label={t("applications.kitPiece.copyOf", { name })}
          onClick={onCopy}
        >
          {t("applications.kitPiece.copy")}
        </Button>
      </div>
    </div>
  );
}
