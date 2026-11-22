import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  listPackets, listShares, newShare, readPacket, readShare, revokeShare, type ShareDetail,
} from "../../api";

const ROOT = ["mentor_reviews"] as const;
const HISTORY = [...ROOT, "history"] as const;

export function useMentorReviews() {
  const [packetId, setPacketId] = useState("");
  const [hours, setHours] = useState(24);
  const [detail, setDetail] = useState<ShareDetail | null>(null);
  const [link, setLink] = useState<{ id: string; url: string } | null>(null);
  const queryClient = useQueryClient();
  const packets = useQuery({
    queryKey: [...ROOT, "packets"], queryFn: ({ signal }) => listPackets(signal),
  });
  const history = useQuery({ queryKey: HISTORY, queryFn: ({ signal }) => listShares(signal) });
  const prepare = useMutation({ mutationFn: readPacket });
  const open = useMutation({ mutationFn: readShare, onSuccess: setDetail });
  const issue = useMutation({ mutationFn: newShare, onSuccess: ({ share, token }) => {
    const url = new URL("/mentor", window.location.origin);
    url.hash = token;
    setLink({ id: share.id, url: url.href });
    prepare.reset();
    void queryClient.invalidateQueries({ queryKey: HISTORY });
  } });
  const revoke = useMutation({ mutationFn: revokeShare, onSuccess: (share) => {
    setDetail(share);
    setLink((before) => before?.id === share.id ? null : before);
    void queryClient.invalidateQueries({ queryKey: HISTORY });
  } });
  const packet = prepare.data?.id === packetId ? prepare.data : null;
  return { packetId, setPacketId, hours, setHours, packet, detail, link, packets, history,
    prepare, open, issue, revoke };
}
