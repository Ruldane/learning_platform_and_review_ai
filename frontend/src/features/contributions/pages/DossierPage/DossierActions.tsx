import { t } from "@/shared/i18n/t";
import { Button, buttonVariants } from "@/shared/ui/button";
import type { Dossier, DossierCommand } from "../../api";
import { PublicationForm } from "../../components/PublicationForm";
import { PullForm } from "../../components/PullForm";

interface Props {
  dossier: Dossier;
  pending: boolean;
  act: (command: DossierCommand) => void;
}

export function DossierActions({ dossier, pending, act }: Props) {
  if (dossier.status === "draft") {
    return (
      <PublicationForm
        repository={dossier.issue.repository}
        base={dossier.base}
        title={dossier.issue.title}
        pending={pending}
        onConfirm={(fields) => act({ kind: "confirm", body: { ...fields, confirm: true } })}
      />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {dossier.publication_url ? (
        <a
          className={buttonVariants({ className: "self-start" })}
          href={dossier.publication_url}
          target="_blank"
          rel="noreferrer"
        >
          {t("contributions.publication.open")}
        </a>
      ) : null}
      {dossier.pull_url ? (
        <a
          href={dossier.pull_url}
          className="underline underline-offset-4"
          target="_blank"
          rel="noreferrer"
        >
          {t("contributions.pull.read")}
        </a>
      ) : (
        <PullForm pending={pending} onTrack={(url) => act({ kind: "pull", url })} />
      )}
      {dossier.pull_url && dossier.status !== "accepted" ? (
        <Button
          aria-disabled={pending}
          className="self-start"
          onClick={() => !pending && act({ kind: "refresh" })}
        >
          {t("contributions.pull.refresh")}
        </Button>
      ) : null}
      {dossier.cv_line ? <p>{t("contributions.cvLine", { line: dossier.cv_line })}</p> : null}
    </div>
  );
}
