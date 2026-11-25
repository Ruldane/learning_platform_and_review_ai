import { useNavigate } from "react-router";
import { BlockCard } from "../../components/BlockCard";
import { ModePicker } from "../../components/ModePicker";
import { toBlockView } from "../../toView";
import type { BlockOut } from "../../types";
import { NoBlockState } from "./NoBlockState";
import type { StartProps } from "./startTypes";

/** The day's block: tutor mode and « Commencer mon bloc », or resuming the open session. */
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
      {openSessionId ? null : (
        <>
          <ModePicker value={mode} onChange={onMode} />
          {starter.launchMenu}
        </>
      )}
      <BlockCard
        block={block ? toBlockView(block) : null}
        openSessionId={openSessionId}
        disabled={starter.pending}
        onStart={() => void starter.start({ mode })}
        onResume={() => void navigate(`/study/session/${openSessionId}`)}
      />
    </>
  );
}
