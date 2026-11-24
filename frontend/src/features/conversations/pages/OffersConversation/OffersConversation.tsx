import { MessageCircle, X } from "lucide-react";
import { Dialog } from "radix-ui";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { OffersChatPanel } from "./OffersChatPanel";

export function OffersConversation() {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <Button variant="outline">
          <MessageCircle aria-hidden="true" />
          {t("conversations.offers.open")}
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <Dialog.Content
          className="fixed top-1/2 left-1/2 z-50 grid h-[min(48rem,calc(100dvh-2rem))]
            w-[calc(100vw-2rem)] max-w-6xl -translate-x-1/2 -translate-y-1/2
            grid-rows-[auto_minmax(0,1fr)] rounded-xl border bg-card shadow-xl outline-none"
        >
          <header className="flex items-start justify-between gap-3 border-b p-4">
            <div>
              <Dialog.Title className="text-lg font-semibold">
                {t("conversations.offers.title")}
              </Dialog.Title>
              <Dialog.Description className="text-sm text-muted-foreground">
                {t("conversations.offers.context")}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label={t("conversations.offers.close")}>
                <X aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </header>
          <OffersChatPanel />
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
