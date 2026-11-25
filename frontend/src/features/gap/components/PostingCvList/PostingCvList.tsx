import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";

export interface PostingCv {
  id: string;
  number: number;
  createdAt: string;
  pdfUrl: string;
}

/** The CVs generated for the posting, each downloadable as PDF; nothing if none is ready. */
export function PostingCvList({ cvs }: { cvs: PostingCv[] }) {
  if (cvs.length === 0) return null;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-lg font-medium">{t("gap.posting.cvsTitle")}</h2>
      <ul className="flex flex-wrap gap-2">
        {cvs.map((cv) => (
          <li key={cv.id}>
            <a href={cv.pdfUrl} download className={buttonVariants({ variant: "outline" })}>
              {t("gap.posting.cvDownload", {
                number: cv.number,
                date: new Date(cv.createdAt).toLocaleDateString("en-GB"),
              })}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
