export const WIDTH = 880;
export const HEIGHT = 500;

export interface Star {
  id: string;
  title: string;
  kind: "skill" | "note";
  gap?: number | null;
}

export interface Point extends Star {
  x: number;
  y: number;
  z: number;
}

export interface Camera {
  yaw: number;
  pitch: number;
  zoom: number;
}

export const INITIAL_CAMERA: Camera = { yaw: 0.36, pitch: -0.21, zoom: 1 };
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

/** Spreads the nodes over a sphere per group, in a stable order. */
export function placeStars(stars: Star[]): Point[] {
  const ordered = [...stars].sort((a, b) => a.id.localeCompare(b.id));
  return ordered.map((star, index) => {
    const y = 1 - (2 * (index + 0.5)) / ordered.length;
    const ring = ordered.length > 1 ? Math.sqrt(1 - y * y) : 0;
    const angle = index * GOLDEN_ANGLE;
    return {
      ...star,
      x: ring * Math.cos(angle) * 1.43,
      y: y * 0.96,
      z: ring * Math.sin(angle),
    };
  });
}

export function projectStars(points: Point[], camera: Camera): Point[] {
  const cosYaw = Math.cos(camera.yaw);
  const sinYaw = Math.sin(camera.yaw);
  const cosPitch = Math.cos(camera.pitch);
  const sinPitch = Math.sin(camera.pitch);
  return points
    .map((star) => {
      const horizontal = star.x * cosYaw - star.z * sinYaw;
      const depth = star.x * sinYaw + star.z * cosYaw;
      const vertical = star.y * cosPitch - depth * sinPitch;
      const z = star.y * sinPitch + depth * cosPitch;
      const factor = (143 * camera.zoom * 3.6) / (3.6 - z);
      return { ...star, x: WIDTH / 2 + horizontal * factor, y: HEIGHT / 2 + vertical * factor, z };
    })
    .sort((a, b) => a.z - b.z);
}

export function closest(points: Point[], x: number, y: number): Point | undefined {
  let distance = 18;
  let selected: Point | undefined;
  for (const point of points) {
    const next = Math.hypot(point.x - x, point.y - y);
    if (next <= distance) {
      selected = point;
      distance = next;
    }
  }
  return selected;
}
