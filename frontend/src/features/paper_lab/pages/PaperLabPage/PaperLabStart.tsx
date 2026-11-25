import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { preparePaperLab } from "../../api";

export function PaperLabStart() {
  const [url, setUrl] = useState("");
  const navigate = useNavigate();
  const client = useQueryClient();
  const start = useMutation({
    mutationFn: () => preparePaperLab(url.trim()),
    onSuccess: ({ lab_id }) => {
      void client.invalidateQueries({ queryKey: ["paperLabs"] });
      void navigate("/learn/papers/" + encodeURIComponent(lab_id));
    },
  });

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (url.trim() && !start.isPending) start.mutate();
      }}
    >
      <label className="flex flex-col gap-1 text-sm font-medium">
        {t("paperLab.url")}
        <input
          type="url"
          required
          maxLength={2083}
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          className="rounded-md border border-input bg-background p-2 focus-visible:ring-2 focus-visible:ring-ring"
        />
      </label>
      <Button type="submit" className="w-fit" disabled={start.isPending}>
        {t("paperLab.prepare")}
      </Button>
      {start.isError ? <p role="alert">{errorMessage(start.error)}</p> : null}
    </form>
  );
}
