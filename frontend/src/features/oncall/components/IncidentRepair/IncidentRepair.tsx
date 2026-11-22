import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface IncidentRepairProps {
  projectUrl: string;
  status: string;
  busy: boolean;
  onDiagnose: () => void;
}

export function IncidentRepair({ projectUrl, status, busy, onDiagnose }: IncidentRepairProps) {
  return (
    <section className="flex flex-col items-start gap-3" aria-labelledby="oncall-repair">
      <h2 id="oncall-repair" className="text-xl font-semibold">
        {t("oncall.diagnosticTitle")}
      </h2>
      <Link className="underline underline-offset-2" to={projectUrl}>
        {t("oncall.openProject")}
      </Link>
      <Button
        variant="secondary"
        aria-disabled={busy}
        onClick={() => {
          if (!busy) onDiagnose();
        }}
      >
        {t("oncall.diagnose")}
      </Button>
      <p role="status">{status}</p>
    </section>
  );
}
