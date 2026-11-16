import { CHANNEL_ORDER, STATUS_ORDER } from "./viewTypes";
import type { ChannelView, StatusView } from "./viewTypes";

/** Une chaîne quelconque est-elle l'un des huit statuts ? (garde de type : aucun cast) */
export const isStatus = (value: string): value is StatusView =>
  STATUS_ORDER.some((status) => status === value);

/** Une chaîne quelconque est-elle l'un des six canaux ? (garde de type : aucun cast) */
export const isChannel = (value: string): value is ChannelView =>
  CHANNEL_ORDER.some((channel) => channel === value);
