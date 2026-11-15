import { useEffect, useRef } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useKitAnnouncement } from "../../hooks/useKitAnnouncement";
import { useSaveKitPiece } from "../../hooks/useSaveKitPiece";
import { useStartKit } from "../../hooks/useStartKit";
import type { KitView } from "../../types";
import { KitControls } from "./KitControls";
import { KitPieces } from "./KitPieces";
import { KitRun } from "./KitRun";
import { useFollowedSession } from "./useFollowedSession";

interface KitBodyProps {
  applicationId: string;
  kit: KitView;
  createSocket?: SocketFactory;
}

/**
 * Le kit lu : une zone vocale (pièce arrivée, kit terminé), les commandes, la session suivie et les
 * sept pièces. Quand January lance le kit, le focus passe à la note « le kit se prépare » : le
 * bouton qu'elle vient d'activer disparaît.
 */
export function KitBody({ applicationId, kit, createSocket }: KitBodyProps) {
  const start = useStartKit(applicationId);
  const save = useSaveKitPiece(applicationId);
  const followed = useFollowedSession(kit, start.sessionId);
  const announcement = useKitAnnouncement(kit);
  const note = useRef<HTMLParagraphElement>(null);
  const focusNote = useRef(false);

  useEffect(() => {
    if (kit.running && focusNote.current) {
      focusNote.current = false;
      note.current?.focus();
    }
  }, [kit.running]);

  async function launch() {
    focusNote.current = true;
    if (!(await start.start())) focusNote.current = false;
  }

  return (
    <div className="flex flex-col gap-4">
      <p role="status" className="sr-only">
        <span key={announcement.count}>{announcement.message}</span>
      </p>
      <KitControls
        applicationId={applicationId}
        pieces={kit.pieces}
        running={kit.running}
        start={start}
        onStart={() => void launch()}
      />
      {followed ? (
        <KitRun
          key={followed}
          applicationId={applicationId}
          sessionId={followed}
          running={kit.running}
          noteRef={note}
          createSocket={createSocket}
        />
      ) : null}
      <KitPieces pieces={kit.pieces} running={kit.running} onSave={save} />
    </div>
  );
}
