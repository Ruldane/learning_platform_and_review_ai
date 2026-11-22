import { useEffect, useMemo, useRef, type PointerEvent } from "react";
import { drawGalaxy, type Link } from "./draw";
import {
  closest,
  HEIGHT,
  placeStars,
  projectStars,
  WIDTH,
  type Camera,
  type Point,
  type Star,
} from "./projection";

interface GalaxyCanvasProps {
  camera: Camera;
  edges: Link[];
  stars: Star[];
  selected: string | null;
  onSelect: (id: string) => void;
  onDrag: (dx: number, dy: number) => void;
}

function hitAt(event: PointerEvent<HTMLCanvasElement>, points: Point[]) {
  const rect = event.currentTarget.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * WIDTH;
  const y = ((event.clientY - rect.top) / rect.height) * HEIGHT;
  return closest(points, x, y);
}

export function GalaxyCanvas({
  camera,
  edges,
  stars,
  selected,
  onSelect,
  onDrag,
}: GalaxyCanvasProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const gesture = useRef<{ x: number; y: number; moved: boolean } | null>(null);
  const positions = useMemo(() => placeStars(stars), [stars]);
  const points = useMemo(() => projectStars(positions, camera), [positions, camera]);
  useEffect(() => {
    const context = canvas.current?.getContext("2d");
    if (context) drawGalaxy(context, points, edges, selected);
  }, [points, edges, selected]);
  function release(event: PointerEvent<HTMLCanvasElement>) {
    if (gesture.current && !gesture.current.moved) {
      const hit = hitAt(event, points);
      if (hit) onSelect(hit.id);
    }
    gesture.current = null;
  }
  return (
    <canvas
      ref={canvas}
      width={WIDTH}
      height={HEIGHT}
      aria-hidden="true"
      className="w-full touch-none rounded-xl bg-[#090f20] cursor-grab active:cursor-grabbing"
      onPointerDown={(event) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        gesture.current = { x: event.clientX, y: event.clientY, moved: false };
      }}
      onPointerMove={(event) => {
        const start = gesture.current;
        if (!start) return;
        const dx = event.clientX - start.x;
        const dy = event.clientY - start.y;
        if (!start.moved && Math.abs(dx) + Math.abs(dy) < 3) return;
        gesture.current = { x: event.clientX, y: event.clientY, moved: true };
        onDrag(dx, dy);
      }}
      onPointerUp={release}
      onPointerCancel={() => {
        gesture.current = null;
      }}
    />
  );
}
