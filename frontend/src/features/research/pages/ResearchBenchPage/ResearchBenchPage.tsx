import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ResearchBenchForm } from "../../components/ResearchBenchForm";
import { useResearchRun } from "../../hooks/useResearchRun";
import { ResearchRun } from "./ResearchRun";

/**
 * Settings > Search test: one query, the Scout searches and reads pages, and the page
 * shows live the queries, the sources kept, discarded and unreadable (10.3). The test is
 * in the URL (`?session=<id>`). `createSocket` serves only the tests (fake WebSocket).
 */
export function ResearchBenchPage({ createSocket }: { createSocket?: SocketFactory }) {
  const run = useResearchRun(createSocket);
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("research.page.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("research.page.intro")}</p>
        <Link to="/settings/search" className="mt-2 inline-block text-sm underline">
          {t("research.page.settingsLink")}
        </Link>
      </header>
      {run.sessionId ? (
        <ResearchRun sessionId={run.sessionId} stream={run.stream} onRestart={run.restart} />
      ) : (
        <>
          <ResearchBenchForm
            launchMenu={run.launchMenu}
            busy={run.start.isPending}
            onSubmit={(input) => run.start.mutate(input)}
          />
          {run.start.error ? <InlineError message={errorMessage(run.start.error)} /> : null}
        </>
      )}
    </div>
  );
}
