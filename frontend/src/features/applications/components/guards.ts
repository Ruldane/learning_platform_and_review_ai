import { CHANNEL_ORDER, STATUS_ORDER } from "./viewTypes";
import type { ChannelView, StatusView } from "./viewTypes";

/** Is any string one of the eight statuses? (type guard: no cast) */
export const isStatus = (value: string): value is StatusView =>
  STATUS_ORDER.some((status) => status === value);

/** Is any string one of the six channels? (type guard: no cast) */
export const isChannel = (value: string): value is ChannelView =>
  CHANNEL_ORDER.some((channel) => channel === value);
