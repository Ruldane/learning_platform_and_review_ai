import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  downloadPacket, listPackets, listSources, previewPacket, readPacket, savePacket,
  type Selection, type Source, type StoredPacket,
} from "../../api";

const HISTORY = ["proof_packets", "history"] as const;
const SOURCES = ["proof_packets", "sources"] as const;
const INITIAL: Selection = { title: "", sources: [] };

export function useProofPackets() {
  const [selection, setSelection] = useState(INITIAL);
  const [stored, setStored] = useState<StoredPacket | null>(null);
  const queryClient = useQueryClient();
  const sources = useQuery({ queryKey: SOURCES, queryFn: ({ signal }) => listSources(signal) });
  const history = useQuery({ queryKey: HISTORY, queryFn: ({ signal }) => listPackets(signal) });
  const preview = useMutation({
    mutationFn: async (form: Selection) => ({ form, packet: await previewPacket(form) }),
    onSuccess: () => setStored(null),
  });
  const save = useMutation({
    mutationFn: savePacket,
    onSuccess: (packet) => {
      setStored(packet);
      void queryClient.invalidateQueries({ queryKey: HISTORY });
    },
  });
  const open = useMutation({ mutationFn: readPacket, onSuccess: (packet) => setStored(packet) });
  const download = useMutation({ mutationFn: downloadPacket });
  const proposed = preview.data?.form === selection ? preview.data.packet : null;
  const setTitle = (title: string) => setSelection((before) => ({ ...before, title }));
  const toggleSource = ({ mission_id, proof_id, revision }: Source) => setSelection((before) => ({
    ...before,
    sources: before.sources.some((source) => source.proof_id === proof_id)
      ? before.sources.filter((source) => source.proof_id !== proof_id)
      : [...before.sources, { mission_id, proof_id, revision }],
  }));
  return {
    selection, setTitle, toggleSource, sources, history, preview, save, open, download, proposed, stored,
  };
}
