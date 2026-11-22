import { HEIGHT, WIDTH, type Point } from "./projection";

export interface Link {
  source: string;
  target: string;
  kind: "prerequisite" | "reference" | "topic";
}

const links = { prerequisite: "#8197db", reference: "#86cad4", topic: "#ba9ce0" };

function renderEdge(
  ctx: CanvasRenderingContext2D,
  points: Map<string, Point>,
  edge: Link,
  selected: string | null,
) {
  const from = points.get(edge.source);
  const to = points.get(edge.target);
  if (!from || !to) return;
  const active = selected === from.id || selected === to.id;
  ctx.globalAlpha = active ? 0.96 : 0.32;
  ctx.strokeStyle = links[edge.kind];
  ctx.lineWidth = active ? 2 : 1;
  ctx.setLineDash(edge.kind === "topic" ? [5, 4] : []);
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();
}

function renderStar(ctx: CanvasRenderingContext2D, point: Point, selected: boolean) {
  const radius = 4.6 + (point.z + 1.6) * 1.2;
  ctx.setLineDash([]);
  ctx.globalAlpha = 1;
  if (selected || (point.gap ?? 0) > 0) {
    ctx.beginPath();
    ctx.strokeStyle = selected ? "#f8faff" : "#ffc36e";
    ctx.lineWidth = selected ? 2.6 : 1.6;
    ctx.arc(point.x, point.y, radius + 4, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.fillStyle = point.kind === "note" ? "#79e8e0" : "#b6c7ff";
  ctx.beginPath();
  ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
  ctx.fill();
  if (selected) {
    const x = Math.min(Math.max(18, point.x + 14), WIDTH - 184);
    const y = Math.max(22, point.y - 14);
    ctx.font = "600 17px system-ui, sans-serif";
    ctx.strokeStyle = "#101b30";
    ctx.lineWidth = 4;
    ctx.strokeText(point.title, x, y, 166);
    ctx.fillStyle = "#f8faff";
    ctx.fillText(point.title, x, y, 166);
  }
}

export function drawGalaxy(
  ctx: CanvasRenderingContext2D,
  points: Point[],
  edges: Link[],
  selected: string | null,
) {
  const sky = ctx.createRadialGradient(WIDTH / 2, HEIGHT / 2, 32, WIDTH / 2, HEIGHT / 2, 540);
  sky.addColorStop(0, "#1e2d4a");
  sky.addColorStop(1, "#090f20");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  const byId = new Map(points.map((point) => [point.id, point]));
  for (const edge of edges) renderEdge(ctx, byId, edge, selected);
  for (const point of points) {
    if (point.id !== selected) renderStar(ctx, point, false);
  }
  const focus = selected ? byId.get(selected) : undefined;
  if (focus) renderStar(ctx, focus, true);
}
