import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { PublicationFields } from "./PublicationFields";

interface PublicationDraft {
  author: string;
  head: string;
  title: string;
  body: string;
}

function draft(form: HTMLFormElement): PublicationDraft {
  const data = new FormData(form);
  return {
    author: String(data.get("author") ?? "").trim(),
    head: String(data.get("head") ?? "").trim(),
    title: String(data.get("title") ?? "").trim(),
    body: String(data.get("body") ?? "").trim(),
  };
}

interface Props {
  repository: string;
  base: string;
  title: string;
  pending: boolean;
  onConfirm: (payload: PublicationDraft) => void;
}

export function PublicationForm({ repository, base, title, pending, onConfirm }: Props) {
  const [confirmed, setConfirmed] = useState(false);
  return (
    <form
      className="flex flex-col gap-3"
      aria-label={t("contributions.publication.label")}
      onChange={(event) => {
        if (!(event.target instanceof HTMLInputElement) || event.target.name !== "confirmation") {
          setConfirmed(false);
        }
      }}
      onSubmit={(event) => {
        event.preventDefault();
        if (!pending && confirmed) onConfirm(draft(event.currentTarget));
      }}
    >
      <p className="text-sm">{t("contributions.publication.base", { repository, base })}</p>
      <PublicationFields title={title} />
      <p className="text-sm text-muted-foreground">{t("contributions.publication.hint")}</p>
      <label className="flex items-center gap-2">
        <input
          name="confirmation"
          type="checkbox"
          checked={confirmed}
          onChange={(event) => setConfirmed(event.currentTarget.checked)}
        />
        {t("contributions.publication.confirm")}
      </label>
      <Button type="submit" className="self-start" aria-disabled={pending || !confirmed}>
        {t("contributions.publication.prepare")}
      </Button>
    </form>
  );
}
