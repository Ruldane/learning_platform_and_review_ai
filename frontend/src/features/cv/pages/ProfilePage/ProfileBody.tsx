import type { SocketFactory } from "@/shared/realtime/socket";
import type { ProfileStateOut } from "../../types";
import { ImportPanel } from "./ImportPanel";
import { ProfileEditor } from "./ProfileEditor";
import { ProfileRun } from "./ProfileRun";

interface ProfileBodyProps {
  state: ProfileStateOut;
  createSocket?: SocketFactory;
}

/** Le corps de la page selon l'état du profil : lecture en cours, rien encore, brouillon ou profil validé. */
export function ProfileBody({ state, createSocket }: ProfileBodyProps) {
  if (state.session_id)
    return <ProfileRun sessionId={state.session_id} createSocket={createSocket} />;
  const current = state.draft ?? state.validated;
  if (current === null) return <ImportPanel />;
  return <ProfileEditor current={current} isDraft={state.draft !== null} />;
}
