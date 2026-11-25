import type { SocketFactory } from "@/shared/realtime/socket";
import type { ProfileStateOut } from "../../types";
import { ImportPanel } from "./ImportPanel";
import { ProfileEditor } from "./ProfileEditor";
import { ProfileRun } from "./ProfileRun";

interface ProfileBodyProps {
  state: ProfileStateOut;
  createSocket?: SocketFactory;
}

/** The page body by profile state: reading in progress, nothing yet, draft or validated profile. */
export function ProfileBody({ state, createSocket }: ProfileBodyProps) {
  if (state.session_id)
    return <ProfileRun sessionId={state.session_id} createSocket={createSocket} />;
  const current = state.draft ?? state.validated;
  if (current === null) return <ImportPanel />;
  return <ProfileEditor current={current} isDraft={state.draft !== null} />;
}
