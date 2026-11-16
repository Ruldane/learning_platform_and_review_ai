import type { SubmissionErrors } from "./rules";
import { DescriptionField } from "./DescriptionField";
import { RepoUrlField } from "./RepoUrlField";
import { ScreenshotPicker } from "./ScreenshotPicker";
import type { RefusedField } from "./useRefusal";

interface SubmissionFieldsProps {
  repoUrl: string;
  description: string;
  screenshots: File[];
  busy: boolean;
  /** Les erreurs de la saisie à montrer (le refus du serveur s'y ajoute par `refused`). */
  errors: SubmissionErrors;
  refused: (field: RefusedField) => string | undefined;
  /** Un champ modifié efface son refus (et celui de « ni lien ni description »). */
  clear: (...fields: RefusedField[]) => void;
  onRepoUrl: (value: string) => void;
  onDescription: (value: string) => void;
  onScreenshots: (files: File[]) => void;
}

/** Les trois champs du rendu : lien du dépôt, description, captures. */
export function SubmissionFields(props: SubmissionFieldsProps) {
  const { errors, refused, clear, busy } = props;
  const missing = errors.missing ?? refused("missing");
  return (
    <>
      <RepoUrlField
        value={props.repoUrl}
        disabled={busy}
        error={errors.repoUrl ?? refused("repoUrl")}
        onChange={(value) => {
          props.onRepoUrl(value);
          clear("repoUrl", "missing");
        }}
      />
      <DescriptionField
        value={props.description}
        disabled={busy}
        error={errors.description ?? refused("description")}
        onChange={(value) => {
          props.onDescription(value);
          clear("description", "missing");
        }}
      />
      <ScreenshotPicker
        files={props.screenshots}
        disabled={busy}
        error={refused("screenshots")}
        onChange={(files) => {
          props.onScreenshots(files);
          clear("screenshots");
        }}
      />
      {missing ? (
        <p role="alert" className="text-sm text-destructive">
          {missing}
        </p>
      ) : null}
    </>
  );
}
