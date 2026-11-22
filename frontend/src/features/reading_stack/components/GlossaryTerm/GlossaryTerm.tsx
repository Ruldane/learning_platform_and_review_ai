interface Props {
  text: string;
  active: boolean;
  onPreview: () => void;
  onOpen: () => void;
  onClose: () => void;
}

export function GlossaryTerm({ text, active, onPreview, onOpen, onClose }: Props) {
  return (
    <button
      type="button"
      className="inline rounded-sm underline decoration-dotted focus-visible:outline focus-visible:outline-2"
      aria-controls={active ? "reading-definition" : undefined}
      aria-describedby={active ? "reading-definition-text" : undefined}
      aria-expanded={active}
      onFocus={onPreview}
      onMouseEnter={onPreview}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
    >
      {text}
    </button>
  );
}
