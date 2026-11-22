export interface NamedOption {
  id: string;
  title: string;
}

export interface RubricView extends NamedOption {
  criteria: { label: string; instructions: string }[];
}

export interface VerdictView {
  winner: "a" | "b" | "tie";
  feedback: string;
  scores: { label: string; a: number | null; b: number | null }[];
  linkA: { href: string; label: string };
  linkB: { href: string; label: string };
}
