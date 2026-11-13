import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { DecideOptions, DecisionView, ModificationView } from "../viewTypes";
import { ConfirmBox } from "./ConfirmBox";
import { DecisionButtons } from "./DecisionButtons";
import { EditField } from "./EditField";
import { Facts } from "./Facts";
import { ModificationDiff } from "./ModificationDiff";
import { ModificationHeader } from "./ModificationHeader";
import { useConfirmation } from "./useConfirmation";

interface ModificationCardProps {
  mod: ModificationView;
  onDecide: (status: DecisionView, opts?: DecideOptions) => void;
  /** Une décision est en route : tout est verrouillé. */
  busy: boolean;
}

/**
 * Une modification proposée : avant / après mot à mot, raison, faits sur lesquels elle s'appuie,
 * auteur. Une modification « à confirmer » ne s'accepte qu'après la case « Je confirme que c'est
 * vrai » ; « Modifier » ouvre un champ et renvoie le texte corrigé.
 */
export function ModificationCard({ mod, onDecide, busy }: ModificationCardProps) {
  const headingId = useId();
  const [editing, setEditing] = useState(false);
  const toConfirm = mod.status === "to_confirm";
  const { confirmed, setConfirmed, opts } = useConfirmation(toConfirm, mod.id, mod.after);
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
      {editing ? (
        <EditField
          initial={mod.after}
          confirmed={confirmed}
          busy={busy}
          onSave={(after) => {
            onDecide("accepted", { after, ...opts });
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <DecisionButtons
          status={mod.status}
          confirmed={confirmed}
          busy={busy}
          onAccept={() => (toConfirm ? onDecide("accepted", opts) : onDecide("accepted"))}
          onRefuse={() => onDecide("refused")}
          onEdit={() => setEditing(true)}
        />
      )}
    </article>
  );
}
