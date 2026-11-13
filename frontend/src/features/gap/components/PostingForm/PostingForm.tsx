import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { FormErrorView, PostingSourceView } from "../viewTypes";
import { PostingTabs, type PostingTab } from "./PostingTabs";
import { SourcePanel } from "./SourcePanel";

interface PostingFormProps {
  /** Un envoi est en route : rien n'est modifiable et « Analyser » est grisé. */
  pending: boolean;
  error: FormErrorView | null;
  onSubmit: (source: PostingSourceView) => void;
}

/**
 * Ajouter une offre : un lien ou le texte collé, en deux onglets. Une offre dont le lien est
 * illisible (`posting_unreadable`) bascule sur l'onglet « Texte » avec le message. Un double clic
 * n'envoie qu'une fois : le formulaire reste verrouillé jusqu'à la réponse de la page.
 */
export function PostingForm({ pending, error, onSubmit }: PostingFormProps) {
  const [tab, setTab] = useState<PostingTab>("url");
  const [values, setValues] = useState({ url: "", text: "" });
  const [seen, setSeen] = useState<FormErrorView | null>(null);
  const sent = useRef(false);
  const ids = { url: useId(), text: useId() };

  // Une réponse (échec, ou fin de l'attente) rouvre le formulaire à l'envoi suivant.
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
      <Button type="submit" className="self-start" disabled={pending || value === ""}>
        {pending ? t("gap.form.pending") : t("gap.form.submit")}
      </Button>
    </form>
  );
}
