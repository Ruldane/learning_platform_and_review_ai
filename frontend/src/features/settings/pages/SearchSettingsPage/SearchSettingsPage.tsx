import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSearchUsage } from "../../hooks/useSearchUsage";
import { useSettings } from "../../hooks/useSettings";
import { SearchSettingsEditor } from "./SearchSettingsEditor";

/** Settings > Web search: languages, engines, domains and the Éclaireur's caps (10.1 to 10.4). */
export function SearchSettingsPage() {
  const settings = useSettings();
  const usage = useSearchUsage();

  const failed = [settings, usage].filter((query) => query.isError);
  if (failed.length > 0) {
    const retry = () => failed.forEach((query) => void query.refetch());
    return <ErrorState message={errorMessage(failed[0]?.error)} onRetry={retry} />;
  }
  if (!settings.data || !usage.data) return <LoadingState label={t("settings.search.loading")} />;
  return <SearchSettingsEditor settings={settings.data} usage={usage.data} />;
}
