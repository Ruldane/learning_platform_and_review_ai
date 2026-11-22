import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  title: string;
  context: string;
  pending: boolean;
  onStart: () => void;
}

export function ScenarioCard({ title, context, pending, onStart }: Props) {
  return (
    <section aria-label={title} className="grid gap-2 rounded border p-3">
      <h2 className="font-semibold">{title}</h2>
      <p>{context}</p>
      <Button type="button" aria-disabled={pending} onClick={() => !pending && onStart()}>
        {t("incidentReplay.start")}
      </Button>
    </section>
  );
}
