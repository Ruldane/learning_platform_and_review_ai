import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ActivityItemView } from "../viewTypes";
import { ActivityRow } from "./ActivityRow";

interface ActivityFeedProps {
  items: ActivityItemView[];
  hasMore: boolean;
  onMore: () => void;
  /** La page suivante est en cours de lecture : « Voir plus » le dit et n'envoie rien de plus. */
  loadingMore?: boolean;
  /** « Maintenant » pour les dates relatives ; l'heure du poste par défaut. */
  now?: Date;
}

/** Le fil d'activité : événements datés (« il y a 5 min », date complète au survol) et « Voir plus ». */
export function ActivityFeed({
  items,
  hasMore,
  onMore,
  loadingMore = false,
  now = new Date(),
}: ActivityFeedProps) {
  return (
    <section
      aria-labelledby="home-activity"
      aria-busy={loadingMore}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <h2 id="home-activity" className="text-lg font-medium">
        {t("home.activity.title")}
      </h2>
      {items.length === 0 ? (
        <p className="text-muted-foreground">{t("home.activity.empty")}</p>
      ) : (
        <ul aria-label={t("home.activity.listLabel")} className="flex flex-col gap-3">
          {items.map((item) => (
            <ActivityRow key={item.id} item={item} now={now} />
          ))}
        </ul>
      )}
      {hasMore ? (
        <Button
          variant="outline"
          className="self-start"
          aria-busy={loadingMore}
          aria-disabled={loadingMore}
          onClick={() => !loadingMore && onMore()}
        >
          {loadingMore ? t("home.activity.loadingMore") : t("home.activity.more")}
        </Button>
      ) : null}
    </section>
  );
}
