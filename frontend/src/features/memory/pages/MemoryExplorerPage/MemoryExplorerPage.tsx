import { useState } from "react";
import { useSearchParams } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ItemPanel } from "./ItemPanel";
import { ListSection } from "./ListSection";
import { PendingSection } from "./PendingSection";
import { SearchSection } from "./SearchSection";
import { StatsSection } from "./StatsSection";

/**
 * Memory explorer: statistics, « À confirmer », search, list and drawer. The open item
 * is in the address (`?item=<id>`): the map and search lead there, and a reload
 * finds it again.
 */
export function MemoryExplorerPage() {
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const itemId = params.get("item");

  const openItem = (id: string) => {
    setCreating(false);
    setParams({ item: id });
  };
  const close = () => {
    setCreating(false);
    setParams({});
  };

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{t("memory.page.explorerTitle")}</h1>
          <p className="mt-2 text-muted-foreground">{t("memory.page.explorerIntro")}</p>
        </div>
        <Button onClick={() => setCreating(true)}>{t("memory.page.add")}</Button>
      </header>
      <StatsSection />
      <PendingSection />
      <SearchSection onOpen={openItem} />
      <section aria-label={t("memory.page.listTitle")}>
        <ListSection onOpen={openItem} />
      </section>
      {/* One key per item: write errors do not carry over from one item to another. */}
      <ItemPanel
        key={creating ? "new" : (itemId ?? "none")}
        itemId={itemId}
        creating={creating}
        onClose={close}
        onOpenItem={openItem}
      />
    </div>
  );
}
