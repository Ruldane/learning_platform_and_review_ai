import { useParams } from "react-router";
import type { SocketFactory } from "@/shared/realtime/socket";
import { KitContent } from "./KitContent";

/**
 * Show the seven kit pieces as they arrive so the user can review, edit, and copy them.
 * Tests can inject a socket factory.
 */
export function KitPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { applicationId = "" } = useParams();
  return (
    <KitContent key={applicationId} applicationId={applicationId} createSocket={createSocket} />
  );
}
