import { useLabOverview } from "@/features/lab/hooks/useLabOverview";
import { useLabPreferences } from "@/features/lab/hooks/useLabPreferences";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { buildDestinations, type Destination } from "../../navigation";
import { FEATURES } from "../../registry";
import { DestinationCards } from "./DestinationCards";
import { LabReadiness } from "./LabReadiness";
import { NavigationPage } from "./NavigationPage";
import { Tour } from "./Tour";

export function LabPage() {
  const cards = buildDestinations(FEATURES).filter((card) => card.section === "lab");
  const { preferences, save } = useLabPreferences();
  const pins = preferences.data?.pinned ?? [];
  const error = preferences.error ?? save.error;
  const overview = useLabOverview();
  const features = overview.data?.sections.flatMap((section) => section.features) ?? [];
  function tools(card: Destination) {
    const pinned = pins.includes(card.id);
    const label = t(pinned ? "navigation.unpin" : "navigation.pin", { name: t(card.labelKey) });
    const missing = features.find((feature) => feature.id === card.id)?.missing_prerequisites ?? [];
    return (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <LabReadiness
          missing={missing}
          pending={overview.isPending}
          unavailable={overview.isError}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-disabled={!preferences.data || save.isPending}
          aria-pressed={pinned}
          onClick={() => {
            if (!preferences.data || save.isPending) return;
            save.mutate({
              pinned: pinned ? pins.filter((id) => id !== card.id) : [...pins, card.id],
            });
          }}
        >
          {label}
        </Button>
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
