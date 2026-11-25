import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { BOARD_PATH } from "../../urls";
import { ManualSection } from "./ManualSection";
import { SentenceSection } from "./SentenceSection";

interface NewApplicationPageProps {
  /** Only for tests (fake WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * A new record (`/applications/new`): in one sentence (the tracking Assistant prepares it and
 * asks for confirmation), or by hand. In both cases, a record that looks like another
 * triggers the duplicate alert, and the created record opens.
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
