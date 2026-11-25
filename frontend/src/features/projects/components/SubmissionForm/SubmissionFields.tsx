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
  /** The input errors to show (the server's refusal is added to them via `refused`). */
  errors: SubmissionErrors;
  refused: (field: RefusedField) => string | undefined;
  /** A changed field clears its refusal (and that of « ni lien ni description »). */
  clear: (...fields: RefusedField[]) => void;
  onRepoUrl: (value: string) => void;
  onDescription: (value: string) => void;
  onScreenshots: (files: File[]) => void;
}

/** The three submission fields: repository link, description, screenshots. */
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
