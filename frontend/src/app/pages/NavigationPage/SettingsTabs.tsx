import { useId, useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import type { Destination, SettingsArea } from "../../navigation";
import { DestinationCards } from "./DestinationCards";

const TABS: readonly SettingsArea[] = ["models", "access", "profile", "advanced"];

export function SettingsTabs({ cards }: { cards: Destination[] }) {
  const [index, setIndex] = useState(0);
  const prefix = useId();
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const area = TABS[index];
  function move(event: KeyboardEvent<HTMLButtonElement>) {
    const next = { Home: 0, End: TABS.length - 1,
      ArrowRight: (index + 1) % TABS.length, ArrowLeft: (index + TABS.length - 1) % TABS.length };
    const destination = next[event.key as keyof typeof next];
    if (destination === undefined) return;
    event.preventDefault();
    setIndex(destination);
    buttons.current[destination]?.focus();
  }
  return (
    <>
      <div role="tablist" aria-label={t("nav.settings")} className="flex flex-wrap gap-2 border-b">
        {TABS.map((tab, position) => (
          <button key={tab} type="button" role="tab" id={`${prefix}-${tab}`}
            ref={(node) => { buttons.current[position] = node; }}
            aria-controls={`${prefix}-panel`} aria-selected={position === index}
            tabIndex={position === index ? 0 : -1} onKeyDown={move} onClick={() => setIndex(position)}
            className={cn("rounded-sm border-b-2 px-3 py-2 text-sm font-medium",
              position === index ? "border-primary text-primary" : "border-transparent")}>
            {t(`navigation.settings.${tab}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${prefix}-panel`} aria-labelledby={`${prefix}-${area}`}>
        <DestinationCards cards={cards.filter(({ settingsArea }) => settingsArea === area)} />
        {area === "access" ? <Link className="mt-4 inline-block underline" to="/memoire/cerveau">
          {t("brain.title")}
        </Link> : null}
        {area === "profile" ? <Link className="mt-4 inline-block underline" to="/carriere/profil">
          {t("cv.nav.profile")}
        </Link> : null}
      </div>
    </>
  );
}
