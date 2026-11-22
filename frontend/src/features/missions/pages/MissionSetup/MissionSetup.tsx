import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { fetchOffer } from "../../api";
import { MissionRequirements } from "../MissionRequirements";

export function MissionSetup({
  postingId,
  onCreated,
}: {
  postingId: string;
  onCreated: () => void;
}) {
  const offer = useQuery({
    queryKey: ["missions", "offer", postingId],
    queryFn: ({ signal }) => fetchOffer(postingId, signal),
  });
  if (offer.isPending) return <LoadingState />;
  if (offer.isError)
    return <ErrorState message={errorMessage(offer.error)} onRetry={() => void offer.refetch()} />;
  return <MissionRequirements offer={offer.data} onCreated={onCreated} />;
}
