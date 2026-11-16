import { t } from "@/shared/i18n/t";
import type { AdviceStatus } from "../viewTypes";

interface AdviceCardProps {
  /** Les deux phrases du conseil, quand il est prêt. */
  sentences: string[] | null;
  status: AdviceStatus;
}

/**
 * Le conseil du jour. `pending` : le conseil se réunit encore (seul état qui change). `failed` et
 * `unavailable` : le conseil n'a rien pu dire, pour toute la journée — quelle qu'en soit la cause,
 * et sans bouton « Réessayer » : le serveur ne relance pas le conseil le même jour.
 */
export function AdviceCard({ sentences, status }: AdviceCardProps) {
  const ready = status === "ready" && sentences !== null && sentences.length > 0;
  return (
    <section
      aria-labelledby="home-advice"
      className="flex flex-col gap-2 rounded-xl border bg-card p-4"
    >
      <h2 id="home-advice" className="text-lg font-medium">
        {t("home.advice.title")}
      </h2>
      {/* Région vocale polie, toujours là : l'arrivée du conseil (ou son échec) est annoncée. */}
      <div aria-live="polite" className="flex flex-col gap-2">
        {ready ? (
          sentences.map((sentence, index) => <p key={`${index}-${sentence}`}>{sentence}</p>)
        ) : status === "pending" ? (
          <p className="text-muted-foreground">{t("home.advice.pending")}</p>
        ) : (
          <p className="text-muted-foreground">{t("home.advice.unavailable")}</p>
        )}
      </div>
    </section>
  );
}
