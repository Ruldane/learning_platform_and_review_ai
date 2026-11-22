import { Button } from "@/shared/ui/button";

interface Props {
  label: string;
  pending: boolean;
  actionLabel: string | null;
  onClick: () => void;
}

export function ConnectionControl({ label, pending, actionLabel, onClick }: Props) {
  return (
    <div className="space-y-3">
      <p role="status">{label}</p>
      {actionLabel ? (
        <Button
          aria-disabled={pending}
          onClick={() => {
            if (!pending) onClick();
          }}
        >
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
