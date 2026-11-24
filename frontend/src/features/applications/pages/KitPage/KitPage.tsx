import { useParams } from "react-router";
import type { SocketFactory } from "@/shared/realtime/socket";
import { KitContent } from "./KitContent";

/**
 * Le kit d'une candidature (`/applications/:applicationId/kit`) : sept pièces préparées par les
 * agents, montrées dès qu'elles sont prêtes, que January relit, modifie et copie. `createSocket` ne
 * sert qu'aux tests.
 */
export function KitPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { applicationId = "" } = useParams();
  return (
    <KitContent key={applicationId} applicationId={applicationId} createSocket={createSocket} />
  );
}
