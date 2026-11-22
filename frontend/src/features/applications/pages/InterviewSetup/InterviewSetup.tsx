import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { PROFILE_PATH } from "../../urls";
import { SettingsFields } from "./SettingsFields";
import { TargetFields } from "./TargetFields";
import { useInterviewSetup } from "./useInterviewSetup";

interface InterviewSetupProps {
  /** La fiche dont c'est l'entretien ; `null` : un entretien sans fiche (offre ou intitulé à choisir). */
  applicationId: string | null;
  /** L'entretien est lancé (ou repris : `resumed`) : la page le suit. */
  onStarted: (interviewId: string, resumed: boolean) => void;
}

/** Les réglages d'un entretien (formule, durée, langue ; et la cible sans fiche), puis « Commencer l'entretien ». */
export function InterviewSetup({ applicationId, onStarted }: InterviewSetupProps) {
  const form = useInterviewSetup(applicationId, onStarted);
  const { launcher } = form;
  return (
    <form
      onSubmit={(event) => void form.submit(event)}
      className="flex flex-col gap-4 rounded-xl border bg-card p-4"
    >
      <h2 className="text-lg font-semibold">{t("applications.interviewSetup.title")}</h2>
      {form.free ? (
        <TargetFields
          draft={form.target}
          postings={form.postings}
          disabled={launcher.pending}
          onChange={form.setTarget}
        />
      ) : null}
      {form.missing ? (
        <p role="alert" className="text-sm text-destructive">
          {t("applications.interviewSetup.target.required")}
        </p>
      ) : null}
      <SettingsFields
        settings={form.settings}
        disabled={launcher.pending}
        onChange={form.setSettings}
      />
      <div className="flex flex-col items-start gap-2">
        {launcher.launchMenu}
        <Button type="submit" disabled={launcher.pending}>
          {t(
            launcher.pending
              ? "applications.interviewSetup.starting"
              : "applications.interviewSetup.start",
          )}
        </Button>
        {launcher.error ? <InlineError message={launcher.error} /> : null}
        {launcher.profileMissing ? (
          <Link
            to={PROFILE_PATH}
            className="text-sm font-medium text-primary underline underline-offset-4"
          >
            {t("applications.interviewSetup.openProfile")}
          </Link>
        ) : null}
      </div>
    </form>
  );
}
