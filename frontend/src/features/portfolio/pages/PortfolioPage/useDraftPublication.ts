import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { getZip, publish, readPreview, type Draft } from "../../api";

async function download(id: string) {
  const blob = await getZip(id);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "portfolio.zip";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function useDraftPublication(value: Draft, reload: () => void) {
  const trigger = useRef<HTMLButtonElement>(null);
  const [approval, setApproval] = useState<string | null>(null);
  const preview = useQuery({
    queryKey: ["portfolio", "preview", value.id],
    queryFn: ({ signal }) => readPreview(value.id, signal),
  });
  const zip = useMutation({ mutationFn: () => download(value.id) });
  const launch = useMutation({
    mutationFn: (destination: string) => publish(value, destination),
    onSuccess: () => {
      setApproval(null);
      reload();
    },
  });
  const cancel = () => {
    setApproval(null);
    requestAnimationFrame(() => trigger.current?.focus());
  };
  return { trigger, approval, setApproval, preview, zip, launch, cancel };
}
