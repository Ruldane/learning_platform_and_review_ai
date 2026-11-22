import type { Selection } from "./api";

export interface ChoiceProps {
  initial: string;
  pending: boolean;
  onChange: () => void;
  onSelect: (body: Selection) => void;
}
