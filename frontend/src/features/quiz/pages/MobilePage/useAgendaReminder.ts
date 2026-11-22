import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import { readUpcomingEvent } from "../../mobile/data";
import { showMobileAlert } from "../../mobile/notifications";

const MINUTE = 60_000;

export function useAgendaReminder(owner: string, enabled: boolean) {
  const { data, dataUpdatedAt, isSuccess } = useQuery({
    queryKey: ["mobile", "agenda", owner],
    queryFn: ({ signal }) => readUpcomingEvent(signal),
    enabled,
    refetchInterval: MINUTE,
    retry: false,
  });
  useEffect(() => {
    if (!enabled || !isSuccess || !data) return;
    const delay = Date.parse(data.start) - Date.now();
    if (!(delay > 0 && delay <= 30 * MINUTE)) return;
    const key = [owner, data.id, data.start].join(":");
    void showMobileAlert("agenda", key, t("mobile.title"), t("mobile.agendaAlert"))
      .catch(() => undefined);
  }, [data, dataUpdatedAt, enabled, isSuccess, owner]);
}
