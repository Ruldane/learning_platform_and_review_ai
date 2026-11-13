import { useNavigate } from "react-router";
import { BlockCard } from "../../components/BlockCard";
import { ModePicker } from "../../components/ModePicker";
import { toBlockView } from "../../toView";
import type { BlockOut } from "../../types";
import { NoBlockState } from "./NoBlockState";
import type { StartProps } from "./startTypes";

/** Le bloc du jour : mode du tuteur et « Commencer mon bloc », ou la reprise de la session ouverte. */
export function DayStart({
  block,
  mode,
  onMode,
  starter,
  openSessionId,
}: StartProps & { block: BlockOut | null }) {
  const navigate = useNavigate();
  if ((!block && !openSessionId) || starter.noBlock) return <NoBlockState />;
  return (
    <>
      {openSessionId ? null : <ModePicker value={mode} onChange={onMode} />}
      <BlockCard
        block={block ? toBlockView(block) : null}
        openSessionId={openSessionId}
        disabled={starter.pending}
        onStart={() => void starter.start({ mode })}
        onResume={() => void navigate(`/etudier/session/${openSessionId}`)}
      />
    </>
  );
}
