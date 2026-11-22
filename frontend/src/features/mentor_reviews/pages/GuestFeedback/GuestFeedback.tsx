import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { GuestReply, Manifest } from "../../api";

interface Props {
  proofs: Manifest["proofs"];
  onSubmit: (reply: GuestReply) => void;
  pending: boolean;
}

export function GuestFeedback({ proofs, onSubmit, pending }: Props) {
  const [selected, setSelected] = useState(proofs[0]?.proof_id ?? "");
  const [text, setText] = useState("");
  return (
    <form className="flex flex-col gap-3" onSubmit={(event) => {
      event.preventDefault();
      onSubmit({ proof_id: selected, text });
    }}>
      <label className="flex flex-col gap-1.5 text-sm">
        <span>{t("mentorReviews.artifact")}</span>
        <select className="rounded-md border border-input bg-background p-2 focus-visible:ring-2 focus-visible:ring-ring"
          value={selected} required onChange={(event) => setSelected(event.target.value)}>
          {proofs.map((proof) => <option key={proof.proof_id} value={proof.proof_id}>
            {t("mentorReviews.source", { title: proof.title, revision: proof.revision })}
          </option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-sm">
        <span>{t("mentorReviews.comment")}</span>
        <textarea className="min-h-32 rounded-md border border-input bg-background p-2 focus-visible:ring-2 focus-visible:ring-ring"
          value={text} maxLength={2000} required onChange={(event) => setText(event.target.value)} />
      </label>
      <Button type="submit" disabled={pending || !text.trim() || !selected} className="self-start">
        {t("mentorReviews.submit")}
      </Button>
    </form>
  );
}
