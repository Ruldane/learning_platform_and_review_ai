import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { BOARD_PATH } from "../../urls";
import { ManualSection } from "./ManualSection";
import { SentenceSection } from "./SentenceSection";

interface NewApplicationPageProps {
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * Une nouvelle fiche (`/applications/new`) : en une phrase (l'Assistant de suivi la prépare et
 * demande confirmation) ou à la main. Dans les deux cas, une fiche qui ressemble à une autre
 * déclenche l'alerte de doublon, et la fiche créée s'ouvre.
 */
export function NewApplicationPage({ createSocket }: NewApplicationPageProps) {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <Link to={BOARD_PATH} className="text-sm underline">
          {t("applications.newPage.back")}
        </Link>
        <h1 className="text-2xl font-semibold">{t("applications.newPage.title")}</h1>
      </header>
      <SentenceSection createSocket={createSocket} />
      <ManualSection />
    </div>
  );
}
