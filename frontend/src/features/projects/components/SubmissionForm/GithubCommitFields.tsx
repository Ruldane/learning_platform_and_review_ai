import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { GithubClaimForm, GithubClaimView } from "../viewTypes";
import { GithubClaimCode } from "./GithubClaimCode";

interface Props {
  form: GithubClaimForm;
  claim: GithubClaimView | null;
  repoUrl: string;
  sha: string;
  onSha: (value: string) => void;
  busy: boolean;
}

export function GithubCommitFields({ form, claim, repoUrl, sha, onSha, busy }: Props) {
  const input = useId();
  const pending = busy || form.pending;
  const permitted = !pending && repoUrl.length > 0 && /^[a-f0-9]{40}$/i.test(sha.trim());
  return (
    <details className="rounded-lg border p-3">
      <summary className="cursor-pointer font-medium focus-visible:outline-2 focus-visible:outline-ring">
        {t("projects.github.title")}
      </summary>
      <div className="mt-3 flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">{t("projects.github.hint")}</p>
        <label htmlFor={input} className="text-sm font-medium">
          {t("projects.github.sha")}
        </label>
        <input
          id={input}
          value={sha}
          maxLength={40}
          disabled={busy}
          className={fieldClass}
          onChange={(event) => onSha(event.target.value)}
        />
        <Button
          type="button"
          variant="outline"
          className="self-start"
          aria-disabled={!permitted}
          onClick={() => {
            if (permitted) form.request({ repoUrl, sha: sha.trim().toLowerCase() });
          }}
        >
          {t(form.pending ? "projects.github.creating" : "projects.github.create")}
        </Button>
        {form.error && (
          <p role="alert" className="text-sm text-destructive">
            {form.error}
          </p>
        )}
        <div aria-live="polite">{claim && <GithubClaimCode {...claim} />}</div>
      </div>
    </details>
  );
}
