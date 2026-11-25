import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { DecideOptions, DecideResult, DecisionView, ModificationView } from "../viewTypes";
import { ConfirmBox } from "./ConfirmBox";
import { DecisionButtons } from "./DecisionButtons";
import { EditField } from "./EditField";
import { Facts } from "./Facts";
import { ModificationDiff } from "./ModificationDiff";
import { ModificationHeader } from "./ModificationHeader";
import { useConfirmation } from "./useConfirmation";
import { useEditing } from "./useEditing";

interface ModificationCardProps {
  mod: ModificationView;
  /** Resolves to `false` if the back end refuses: the editor stays open with the typed text. */
  onDecide: (status: DecisionView, opts?: DecideOptions) => DecideResult;
  /** A decision is under way: everything is locked. */
  busy: boolean;
  /** The back end's refusal for this card (« mot clé absent du profil »…). */
  error?: string | null;
}

/**
 * A proposed modification: before / after word by word, reason, the facts it relies on,
 * and author. A modification marked « à confirmer » can only be accepted after the
 * « Je confirme que c'est vrai » checkbox. « Modifier » (rewrite or addition only) opens a
 * field and returns the corrected text, without confirmation: the back end re-checks it, and
 * the checkbox is required again if new blocks appear.
 */
export function ModificationCard({ mod, onDecide, busy, error = null }: ModificationCardProps) {
  const headingId = useId();
  const toConfirm = mod.status === "to_confirm";
  const { confirmed, setConfirmed, opts } = useConfirmation(toConfirm, mod.id, mod.after);
  const edit = useEditing(mod, opts, onDecide);
  return (
    <article
      aria-labelledby={headingId}
      aria-busy={busy}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      <ModificationHeader mod={mod} headingId={headingId} />
      <ModificationDiff before={mod.before} after={mod.after} />
      <p className="text-sm">
        <span className="font-medium">{t("cv.mod.reason")} : </span>
        {mod.reason}
      </p>
      <Facts facts={mod.facts} />
      {toConfirm ? (
        <ConfirmBox
          blocks={mod.blocks}
          confirmed={confirmed}
          disabled={busy}
          onChange={setConfirmed}
        />
      ) : null}
      {edit.editing ? (
        <EditField
          initial={mod.after}
          confirmed={confirmed}
          busy={busy}
          onSave={edit.save}
          onCancel={edit.close}
        />
      ) : (
        <DecisionButtons
          status={mod.status}
          confirmed={confirmed}
          busy={busy}
          onAccept={() => (toConfirm ? onDecide("accepted", opts) : onDecide("accepted"))}
          onRefuse={() => onDecide("refused")}
          onEdit={mod.action === "rewrite" || mod.action === "add" ? edit.open : null}
        />
      )}
      {error ? <InlineError message={error} /> : null}
    </article>
  );
}
