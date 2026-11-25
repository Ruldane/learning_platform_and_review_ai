import type { components } from "@/shared/api/schema";
import type {
  DocumentRow,
  ItemFilterValue,
  MapPointView,
  MemoryItemDetailView,
  MemoryItemRow,
  SearchHitView,
} from "./components/viewTypes";

export type {
  DocumentRow,
  DocumentStatusView,
  ItemEdit,
  ItemPatch,
  ItemFilterValue,
  MapPointView,
  MemoryItemDetailView,
  MemoryItemRow,
  MemoryKindView,
  MemoryStatsView,
  NewItem,
  ReindexView,
  SearchHitView,
} from "./components/viewTypes";

type Schemas = components["schemas"];

export type DocumentCreated = Schemas["DocumentCreated"];
export type DocumentOut = Schemas["DocumentOut"];
export type SessionView = Schemas["SessionView"];
export type MapResponse = Schemas["MapResponse"];
export type MemoryItemDetail = Schemas["MemoryItemDetail"];
export type MemoryItemList = Schemas["MemoryItemList"];
export type MemoryItemOut = Schemas["MemoryItemOut"];
export type MemoryWriteOut = Schemas["MemoryWriteOut"];
export type ReindexState = Schemas["ReindexState"];
export type SearchHitOut = Schemas["SearchHitOut"];
export type SearchResponse = Schemas["SearchResponse"];
export type StatsOut = Schemas["StatsOut"];

/** Item status: `pending` = decision proposed by an agent, awaiting agreement. */
export type ItemStatus = "active" | "pending";

/** A page of the list: screen filters, status, position and page size. */
export interface ItemsQuery {
  filters: ItemFilterValue;
  status: ItemStatus;
  offset: number;
  limit: number;
}

/** What the user sends to `POST /documents` or `POST /documents/text`. */
export type UploadInput =
  | { kind: "file"; file: File }
  | { kind: "url"; url: string }
  | { kind: "text"; text: string; title: string };

type Assert<T extends true> = T;

/** Checked at compile time: the generated types satisfy the components' view types. */
export type ViewTypesMatchContract = [
  Assert<
    MemoryItemOut extends Pick<MemoryItemRow, "id" | "kind" | "title" | "tags"> ? true : false
  >,
  Assert<MemoryItemDetail extends Pick<MemoryItemDetailView, "text" | "evidence"> ? true : false>,
  Assert<SearchHitOut extends SearchHitView ? true : false>,
  Assert<MapResponse["points"][number] extends MapPointView ? true : false>,
  Assert<DocumentOut["status"] extends DocumentRow["status"] ? true : false>,
];
