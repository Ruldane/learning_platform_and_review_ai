import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface PostingOutcomeProps {
  status: "rejected" | "failed";
  reason: string | null;
  relaunching: boolean;
  error: string | null;
  onRelaunch: () => void;
}

/**
 * Une offre refusée (« ce n'est pas une offre ») ou dont l'analyse s'est arrêtée. Seule la
 * seconde se relance ; la première se supprime ou se remplace par un autre envoi.
 */
export function PostingOutcome({
  status,
  reason,
  relaunching,
  error,
  onRelaunch,
}: PostingOutcomeProps) {
  const rejected = status === "rejected";
  return (
    <section
      aria-label={t(rejected ? "gap.posting.rejectedTitle" : "gap.posting.failedTitle")}
      className="flex flex-col items-start gap-2 rounded-xl border bg-card p-4"
    >
      <h2 className="text-lg font-medium">
        {t(rejected ? "gap.posting.rejectedTitle" : "gap.posting.failedTitle")}
      </h2>
      <p className="text-sm text-muted-foreground">
        {reason ?? t(rejected ? "gap.posting.rejectedDefault" : "gap.posting.failedDefault")}
      </p>
      {error ? <InlineError message={error} /> : null}
      {rejected ? null : (
        <Button onClick={onRelaunch} disabled={relaunching}>
          {relaunching ? t("gap.posting.relaunching") : t("gap.posting.relaunch")}
        </Button>
      )}
    </section>
  );
}
