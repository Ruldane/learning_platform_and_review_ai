import { t } from "@/shared/i18n/t";

/** Forme de `GET /health/embedding` (types générés ; non importés : la règle de découpage). */
interface EmbeddingProgressView {
  model: string;
  present: boolean;
  /** De 0 à 100 ; vide tant que la taille n'est pas connue. */
  percent: number | null;
  /** Un texte français sans donnée personnelle. */
  detail: string;
}

interface EmbeddingProgressBarProps {
  progress?: EmbeddingProgressView;
  /** La dernière lecture a échoué (le prochain tour réessaie tout seul). */
  isError: boolean;
}

function summary({ model, present, percent }: EmbeddingProgressView): string {
  if (present) return t("onboarding.embedding.ready", { model });
  if (percent === null) return t("onboarding.embedding.waiting", { model });
  return t("onboarding.embedding.percent", { model, percent });
}

/**
 * La progression du modèle d'embeddings : la phrase (« bge-m3 : 42 % ») dit l'état, la barre le
 * montre. Une taille encore inconnue donne une barre sans valeur et le détail du serveur. La zone
 * `status` est toujours dans la page : elle ne dit que ce qui vaut une annonce (« prêt », ou la
 * lecture impossible), pas chaque pourcentage relu toutes les 3 s.
 */
export function EmbeddingProgressBar({ progress, isError }: EmbeddingProgressBarProps) {
  const ready = progress?.present === true;
  const announcement = (() => {
    if (isError) return t("onboarding.embedding.unreadable");
    return progress && ready ? summary(progress) : "";
  })();
  return (
    <div className="flex flex-col gap-2">
      <p
        role="status"
        className={`text-sm empty:sr-only ${isError ? "text-destructive" : "font-medium"}`}
      >
        {announcement}
      </p>
      {progress ? (
        <>
          {ready ? null : <p className="text-sm font-medium">{summary(progress)}</p>}
          <progress
            aria-label={t("onboarding.embedding.label")}
            max={100}
            value={progress.percent ?? undefined}
            className="h-2 w-full max-w-md"
          />
          {!progress.present && progress.detail ? (
            <p className="text-sm text-muted-foreground">{progress.detail}</p>
          ) : null}
          {!progress.present ? (
            <p className="text-sm text-muted-foreground">{t("onboarding.embedding.hint")}</p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
