import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { FormErrorView, PostingSourceView } from "../viewTypes";
import { PostingTabs, type PostingTab } from "./PostingTabs";
import { SourcePanel } from "./SourcePanel";

interface PostingFormProps {
  /** A submission is in progress: nothing is editable and « Analyser » is greyed out. */
  pending: boolean;
  error: FormErrorView | null;
  launchOptions?: ReactNode;
  onSubmit: (source: PostingSourceView) => void;
}

/**
 * Add a posting: a link or the pasted text, in two tabs. A posting whose link is
 * unreadable (`posting_unreadable`) switches to the « Texte » tab, with its message. A double
 * click submits only once: the form stays locked until the page responds.
 */
export function PostingForm({ pending, error, launchOptions, onSubmit }: PostingFormProps) {
  const [tab, setTab] = useState<PostingTab>("url");
  const [values, setValues] = useState({ url: "", text: "" });
  const [seen, setSeen] = useState<FormErrorView | null>(null);
  const sent = useRef(false);
  const ids = { url: useId(), text: useId() };

  // A response (failure, or end of the wait) reopens the form for the next submission.
  useEffect(() => {
    if (!pending) sent.current = false;
  }, [pending, error]);

  if (error !== seen) {
    setSeen(error);
    if (error?.code === "posting_unreadable") setTab("text");
  }

  const value = values[tab].trim();
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (pending || sent.current || value === "") return;
    sent.current = true;
    onSubmit(tab === "url" ? { url: value } : { text: value });
  };
  const panel = (kind: PostingTab) => (
    <SourcePanel
      kind={kind}
      id={ids[kind]}
      hidden={tab !== kind}
      value={values[kind]}
      disabled={pending}
      onChange={(next) => setValues({ ...values, [kind]: next })}
    />
  );

  return (
    <form
      onSubmit={submit}
      aria-label={t("gap.form.label")}
      aria-busy={pending}
      className="flex flex-col gap-3"
    >
      <PostingTabs tab={tab} ids={ids} onChange={setTab} />
      {panel("url")}
      {panel("text")}
      {error ? <InlineError message={error.message} /> : null}
      {launchOptions}
      <Button type="submit" className="self-start" disabled={pending || value === ""}>
        {pending ? t("gap.form.pending") : t("gap.form.submit")}
      </Button>
    </form>
  );
}
