import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { useLaunchSource } from "@/shared/session-ui";
import { PostingPicker } from "../../components/PostingPicker";
import { usePostingTitles } from "../../hooks/useVersions";

/**
 * On the templates page: pick an analysed posting and open its review
 * (`/career/cv/reviews/new/:postingId`), which leads to the CV generated for it.
 */
export function TemplatePostingPicker() {
  const navigate = useNavigate();
  const provider = useLaunchSource();
  const postings = usePostingTitles();
  const ready = (postings.data ?? [])
    .filter((posting) => posting.status === "ready")
    .map((posting) => ({
      id: posting.id,
      label:
        [posting.title, posting.company].filter(Boolean).join(" — ") ||
        t("cv.postingPicker.untitled"),
    }));
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">{t("cv.postingPicker.title")}</h2>
      <p className="max-w-prose text-sm text-muted-foreground">{t("cv.postingPicker.hint")}</p>
      {postings.data === undefined ? null : (
        <>
          {ready.length > 0 ? provider.menu : null}
          <PostingPicker
            postings={ready}
            onPick={(postingId) =>
              void navigate(`/career/cv/reviews/new/${postingId}`, {
                state: { runSource: provider.source },
              })
            }
          />
        </>
      )}
    </section>
  );
}
