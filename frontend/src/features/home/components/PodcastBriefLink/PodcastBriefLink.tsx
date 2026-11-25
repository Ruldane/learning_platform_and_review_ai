import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

export function PodcastBriefLink() {
  return (
    <Link
      className="rounded-xl border bg-card p-4 font-medium underline underline-offset-4"
      to="/study/podcast"
    >
      {t("podcast.title")}
    </Link>
  );
}
