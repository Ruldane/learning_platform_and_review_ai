import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { MAX_CONTACTS } from "../viewTypes";
import type { ContactView } from "../viewTypes";
import { ContactRow } from "./ContactRow";

interface ContactListProps {
  contacts: ContactView[];
  /** Receives the whole list after each addition, removal or keystroke. */
  onChange: (contacts: ContactView[]) => void;
}

const EMPTY: ContactView = { id: "", name: "", role: null, url: null };

/** Editing a record's contacts: ten at most (server limit). */
export function ContactList({ contacts, onChange }: ContactListProps) {
  const full = contacts.length >= MAX_CONTACTS;
  return (
    <div role="group" aria-label={t("applications.contacts.label")} className="flex flex-col gap-2">
      {contacts.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("applications.contacts.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {contacts.map((contact, index) => (
            <ContactRow
              key={index}
              contact={contact}
              rank={index + 1}
              onChange={(next) =>
                onChange(contacts.map((item, at) => (at === index ? next : item)))
              }
              onRemove={() => onChange(contacts.filter((_, at) => at !== index))}
            />
          ))}
        </ul>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={full}
          onClick={() => onChange([...contacts, EMPTY])}
        >
          {t("applications.contacts.add")}
        </Button>
        {full && <p className="text-xs text-muted-foreground">{t("applications.contacts.max")}</p>}
      </div>
    </div>
  );
}
