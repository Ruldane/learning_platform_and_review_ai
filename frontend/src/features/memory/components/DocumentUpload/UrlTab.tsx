import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface UrlTabProps {
  busy: boolean;
  onSubmitUrl: (url: string) => void;
}

/** Import d'un lien (page web ou vidéo YouTube) ; le serveur valide l'adresse. */
export function UrlTab({ busy, onSubmitUrl }: UrlTabProps) {
  const [url, setUrl] = useState("");
  const trimmed = url.trim();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!busy && trimmed !== "") onSubmitUrl(trimmed);
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm font-medium">
        {t("memory.upload.urlLabel")}
        <input
          type="url"
          value={url}
          disabled={busy}
          onChange={(event) => setUrl(event.target.value)}
          className={fieldClass}
        />
      </label>
      <p className="text-sm text-muted-foreground">{t("memory.upload.urlHint")}</p>
      <Button type="submit" disabled={busy || trimmed === ""} className="self-start">
        {t("memory.upload.urlSubmit")}
      </Button>
    </form>
  );
}
