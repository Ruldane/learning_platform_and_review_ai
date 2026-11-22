import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

export function PullForm({
  pending,
  onTrack,
}: {
  pending: boolean;
  onTrack: (url: string) => void;
}) {
  const [value, setValue] = useState("");
  const id = useId();
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!pending && value.trim()) onTrack(value.trim());
      }}
    >
      <label htmlFor={id} className="text-sm font-medium">
        {t("contributions.pull.label")}
      </label>
      <input
        id={id}
        type="url"
        required
        maxLength={350}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        className={fieldClass}
      />
      <Button type="submit" className="self-start" aria-disabled={pending || value.trim() === ""}>
        {t("contributions.pull.track")}
      </Button>
    </form>
  );
}
