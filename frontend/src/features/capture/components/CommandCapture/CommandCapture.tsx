import { X } from "lucide-react";
import { Dialog } from "radix-ui";
import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface CommandCaptureProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The input field, or the tracking of the running capture. */
  children: ReactNode;
}

/**
 * Quick capture: a modal dialog. Focus stays trapped in the dialog, Escape closes it, and
 * focus returns to the element that opened it. Never `window.confirm`: nothing is lost on
 * close (a running capture is found again when reopening with Ctrl+K).
 */
export function CommandCapture({ open, onOpenChange, children }: CommandCaptureProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-150" />
        <Dialog.Content className="fixed top-[8vh] left-1/2 z-50 flex max-h-[84vh] w-[min(42rem,calc(100vw-2rem))] -translate-x-1/2 flex-col gap-4 overflow-y-auto rounded-xl border border-border bg-card p-5 shadow-lg outline-none motion-safe:animate-in motion-safe:fade-in motion-safe:duration-150">
          <header className="flex items-start justify-between gap-3">
            <div>
              <Dialog.Title className="text-lg font-semibold">
                {t("capture.dialog.title")}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-muted-foreground">
                {t("capture.dialog.description")}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label={t("capture.dialog.close")}>
                <X aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </header>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
