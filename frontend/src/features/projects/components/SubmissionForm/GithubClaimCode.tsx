import { t } from "@/shared/i18n/t";
import type { GithubClaimView } from "../viewTypes";

export function GithubClaimCode({
  code,
  profileUrl,
}: Pick<GithubClaimView, "code" | "profileUrl">) {
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p>{t("projects.github.instructions")}</p>
      <code className="select-all break-all">{code}</code>
      <a
        href={profileUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="self-start underline"
      >
        {t("projects.github.profile")}
      </a>
    </div>
  );
}
