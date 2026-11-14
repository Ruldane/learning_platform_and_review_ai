import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { POLL_MS, useProfile } from "../../hooks/useProfile";
import { ProfileBody } from "./ProfileBody";

interface ProfilePageProps {
  /** Intervalle de relecture, en ms (réduit par les tests). */
  pollMs?: number;
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * Le profil maître (`/carriere/profil`). Sans profil : l'import des documents. Pendant la lecture :
 * le fil de l'Archiviste. Un brouillon se relit puis se valide (`PUT` avec la version relue) ; un
 * profil validé se corrige de la même façon. L'historique des versions est dessous.
 */
export function ProfilePage({ pollMs = POLL_MS, createSocket }: ProfilePageProps) {
  const query = useProfile(pollMs);
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{t("cv.profilePage.title")}</h1>
        <p className="text-muted-foreground">{t("cv.profilePage.intro")}</p>
      </header>
      {query.data === undefined ? (
        query.isError ? (
          <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
        ) : (
          <LoadingState label={t("cv.profilePage.loading")} />
        )
      ) : (
        <ProfileBody state={query.data} createSocket={createSocket} />
      )}
    </div>
  );
}
