import { useApiKeys } from "@/features/settings/hooks/useApiKeys";
import { useSettings } from "@/features/settings/hooks/useSettings";
import { Link } from "react-router";
import { useLabPreferences } from "@/features/lab/hooks/useLabPreferences";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { buildDestinations, type Destination } from "../../navigation";
import { FEATURES } from "../../registry";
import { DestinationCards } from "./DestinationCards";
import { NavigationPage } from "./NavigationPage";
import { Tour } from "./Tour";

export function LabPage() {
  const cards = buildDestinations(FEATURES).filter((card) => card.section === "lab");
  const { preferences, save } = useLabPreferences();
  const keys = useApiKeys();
  const settings = useSettings();
  const pins = preferences.data?.pinned ?? [];
  const error = preferences.error ?? save.error;
  const available = keys.data?.filter((key) => key.source && key.readable).map((key) => key.provider);
  const configured = (["rapide", "standard", "fort"] as const)
    .every((tier) => available?.includes(settings.data?.tiers?.[tier]?.provider ?? ""));
  function tools(card: Destination) {
    const pinned = pins.includes(card.id);
    const label = t(pinned ? "navigation.unpin" : "navigation.pin", { name: t(card.labelKey) });
    const ready = !card.modelsRequired || configured;
    const status = ready ? "ready" : keys.isPending ? "checking" : keys.isError ? "unknown" : "configure";
    return (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="grid gap-1">
          <p className="text-sm font-medium text-muted-foreground">{t(`navigation.${status}`)}</p>
          {status === "configure" ? <Link to="/reglages/modeles" className="text-sm underline">
            {t("navigation.modelsLink")}
          </Link> : null}
        </div>
        <Button type="button" variant="outline" size="sm" aria-disabled={!preferences.data || save.isPending}
          aria-pressed={pinned} onClick={() => {
            if (!preferences.data || save.isPending) return;
            save.mutate({ pinned: pinned ? pins.filter((id) => id !== card.id) : [...pins, card.id] });
          }}>{label}</Button>
      </div>
    );
  }
  return (
    <NavigationPage section="lab">
      <Tour />
      {error ? <InlineError message={errorMessage(error)} /> : null}
      <DestinationCards cards={cards} tools={tools} />
    </NavigationPage>
  );
}
