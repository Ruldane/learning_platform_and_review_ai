import { useSearchParams } from "react-router";

export function useBrainSelection() {
  const [params, setParams] = useSearchParams();
  const select = (id: string | null) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (id) next.set("conversation", id);
      else next.delete("conversation");
      return next;
    });
  return { requested: params.get("conversation"), select };
}
