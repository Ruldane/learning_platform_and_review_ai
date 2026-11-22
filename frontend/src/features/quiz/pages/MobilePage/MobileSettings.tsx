import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { MobileSnapshot } from "../../mobile/data";
import { showMobileAlert } from "../../mobile/notifications";
import { clearMobile } from "../../mobile/storage";
import { pinSnapshot } from "./useMobileReview";
import { useAgendaReminder } from "./useAgendaReminder";

export function MobileSettings({ snapshot, pinned }: { snapshot: MobileSnapshot; pinned: boolean }) {
  const [permission, setPermission] = useState(
    () => "Notification" in window ? Notification.permission : null,
  );
  const prepare = useMutation({ mutationFn: () => pinSnapshot(snapshot) });
  const count = snapshot.offers.length;
  const day = snapshot.day;
  const owner = snapshot.owner;
  useAgendaReminder(owner, permission === "granted");
  useEffect(() => {
    if (count > 0 && permission === "granted") {
      void showMobileAlert("offers", owner + ":" + day, t("mobile.title"), t("mobile.offerAlert", { count }))
        .catch(() => undefined);
    }
  }, [count, day, owner, permission]);
  return (
    <div className="flex flex-wrap gap-2">
      {pinned ? (
        <Button variant="outline" onClick={clearMobile}>{t("mobile.clear")}</Button>
      ) : (
        <Button aria-disabled={prepare.isPending}
          onClick={() => !prepare.isPending && prepare.mutate()}>{t("mobile.prepare")}</Button>
      )}
      {permission === "default" ? (
        <Button variant="outline"
          onClick={() => void Notification.requestPermission().then(setPermission).catch(() => undefined)}>
          {t("mobile.enableAlerts")}
        </Button>
      ) : null}
      {prepare.error ? <p role="alert">{t("mobile.prepareError")}</p> : null}
    </div>
  );
}
