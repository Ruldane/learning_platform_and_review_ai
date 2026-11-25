import { useRef } from "react";
import { useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ConnectionControl } from "../../components/ConnectionControl";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { Synchronize } from "../Synchronize";
import { useCalendarConnection } from "./useCalendarConnection";

const actions = {
  disconnected: "connect",
  connected: "disconnect",
  revocation_pending: "retryRevoke",
  unconfigured: null,
} as const;

export function CalendarPage() {
  const [params] = useSearchParams();
  const heading = useRef<HTMLHeadingElement>(null);
  const { query, status, error, pending, connect, disconnect } = useCalendarConnection();
  const action = status && actions[status];
  return (
    <div className="flex max-w-2xl flex-col gap-5">
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">
        {t("calendar.title")}
      </h1>
      <p>{t("calendar.permissions")}</p>
      {query.isPending ? <LoadingState label={t("calendar.loading")} /> : null}
      {query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : null}
      {(params.get("calendar") ?? params.get("agenda")) === "error" && status === "disconnected" ? (
        <p role="alert">{t("calendar.callbackError")}</p>
      ) : null}
      {error ? <p role="alert">{errorMessage(error)}</p> : null}
      {status ? (
        <ConnectionControl
          label={t(`calendar.status.${status}`)}
          pending={pending}
          actionLabel={action ? t(`calendar.${action}`) : null}
          onClick={() => {
            if (status === "disconnected") connect();
            else {
              heading.current?.focus();
              disconnect();
            }
          }}
        />
      ) : null}
      {status === "connected" && !pending ? (
        <Synchronize
          initialProgram={params.get("program") ?? params.get("programme") ?? ""}
          initialApplication={params.get("application") ?? params.get("entretien") ?? ""}
        />
      ) : null}
    </div>
  );
}
