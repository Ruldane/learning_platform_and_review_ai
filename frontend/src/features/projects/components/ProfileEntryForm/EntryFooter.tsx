import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface EntryFooterProps {
  added: boolean;
  /** The version of the master profile that received the entry, when known. */
  version?: number | null;
  busy: boolean;
  /** The button click: the only action that adds the entry (Enter in a field sends nothing). */
  onAdd: () => void;
}

/**
 * The form footer: the consent reminder, then the add button, which the « Ajouté au
 * profil (version N) » state replaces once the entry is in the profile. The status region stays
 * in place: the change is announced, and it takes focus back from the button that disappears.
 */
export function EntryFooter({ added, version = null, busy, onAdd }: EntryFooterProps) {
  const status = useRef<HTMLParagraphElement>(null);
  const wasAdded = useRef(added);
  useEffect(() => {
    // The clicked button was just replaced: focus would have fallen to `body`.
    if (added && !wasAdded.current && document.activeElement === document.body) {
      status.current?.focus();
    }
    wasAdded.current = added;
  }, [added]);
  return (
    <>
      <p className="text-sm text-muted-foreground">{t("projects.entry.notice")}</p>
      <p ref={status} tabIndex={-1} role="status" className="text-sm font-medium outline-none">
        {added
          ? version === null
            ? t("projects.entry.added")
            : t("projects.entry.addedVersion", { version })
          : null}
      </p>
      {added ? null : (
        <Button
          type="button"
          className="self-start"
          aria-disabled={busy}
          onClick={() => !busy && onAdd()}
        >
          {busy ? t("projects.entry.adding") : t("projects.entry.add")}
        </Button>
      )}
    </>
  );
}
