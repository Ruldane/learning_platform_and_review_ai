import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { POLL_MS, useProfile } from "../../hooks/useProfile";
import { ProfileBody } from "./ProfileBody";

interface ProfilePageProps {
  /** Reload interval, in ms (reduced by the tests). */
  pollMs?: number;
  /** Only used by the tests (fake WebSocket). */
  createSocket?: SocketFactory;
}

/**
 * The master profile (`/career/profile`). Without a profile: the document import. While reading:
 * the Archiviste's thread. A draft is reviewed, then validated (`PUT` with the reviewed version); a
 * validated profile is fixed the same way. The version history is below.
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
