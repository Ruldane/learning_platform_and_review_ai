import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useMcpSettings } from "../../hooks/useMcpSettings";
import { ConfirmationsSection } from "./ConfirmationsSection";
import { HistorySection } from "./HistorySection";
import { LevelsSection } from "./LevelsSection";
import { RelaySection } from "./RelaySection";
import { SwitchSection } from "./SwitchSection";
import { TokensSection } from "./TokensSection";

/**
 * Réglages > Accès MCP : l'interrupteur général, les jetons, les demandes « À confirmer »,
 * l'historique de ce que Claude a fait (avec « Annuler ») et la table des niveaux. L'interrupteur
 * coupé ne referme pas la lecture : on voit toujours ce qui a eu lieu, on ne crée plus de jeton.
 */
export function McpAccessPage() {
  const settings = useMcpSettings();
  return (
    <div className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("mcp.page.title")}</h1>
        <p className="mt-1 max-w-prose text-muted-foreground">{t("mcp.page.intro")}</p>
      </header>
      {settings.isPending ? <LoadingState label={t("mcp.page.loading")} /> : null}
      {settings.isError ? (
        <ErrorState
          message={errorMessage(settings.error)}
          onRetry={() => void settings.refetch()}
        />
      ) : null}
      {settings.data ? (
        <>
          <SwitchSection enabled={settings.data.enabled} />
          <RelaySection enabled={settings.data.enabled} />
          <TokensSection enabled={settings.data.enabled} />
          <ConfirmationsSection />
          <HistorySection />
          <LevelsSection />
        </>
      ) : null}
    </div>
  );
}
