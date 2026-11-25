import { useId } from "react";
import { Trash2 } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ContactView } from "../viewTypes";

interface ContactRowProps {
  contact: ContactView;
  /** Rank starting at 1, to name the fields. */
  rank: number;
  onChange: (contact: ContactView) => void;
  onRemove: () => void;
}

/** A contact: name (required), role and profile address (optional). */
export function ContactRow({ contact, rank, onChange, onRemove }: ContactRowProps) {
  const errorId = useId();
  const missingName = contact.name.trim() === "";
  const optional = (value: string) => (value === "" ? null : value);
  return (
    <li className="flex flex-col gap-1">
      <div className="flex flex-wrap items-start gap-2">
        <input
          aria-label={t("applications.contacts.nameField", { rank })}
          aria-invalid={missingName}
          aria-describedby={missingName ? errorId : undefined}
          className={`${fieldClass} sm:w-48 sm:flex-1`}
          value={contact.name}
          onChange={(event) => onChange({ ...contact, name: event.target.value })}
        />
        <input
          aria-label={t("applications.contacts.roleField", { rank })}
          className={`${fieldClass} sm:w-48 sm:flex-1`}
          value={contact.role ?? ""}
          onChange={(event) => onChange({ ...contact, role: optional(event.target.value) })}
        />
        <input
          type="text"
          inputMode="url"
          aria-label={t("applications.contacts.urlField", { rank })}
          className={`${fieldClass} sm:w-56 sm:flex-1`}
          value={contact.url ?? ""}
          onChange={(event) => onChange({ ...contact, url: optional(event.target.value) })}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={t("applications.contacts.remove", { name: contact.name || `n° ${rank}` })}
          onClick={onRemove}
        >
          <Trash2 aria-hidden="true" />
        </Button>
      </div>
      {missingName && (
        <p id={errorId} className="text-xs text-destructive">
          {t("applications.contacts.nameRequired")}
        </p>
      )}
    </li>
  );
}
