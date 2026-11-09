import { readFileSync } from "fs";
import path from "path";

/**
 * Injecte en inline le sprite SVG HugeIcons (public/design/icons.svg) une
 * seule fois dans le <body>. Les composants <Icon name="..."/> référencent
 * ensuite chaque symbole via <use href="#i-X"/>. Server component : lu au
 * build, pas de fetch côté client.
 */
export function IconSprite() {
  const spritePath = path.join(process.cwd(), "public", "design", "icons.svg");
  let svg = "";
  try {
    svg = readFileSync(spritePath, "utf8");
  } catch {
    svg = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none"></svg>';
  }
  return (
    <div
      aria-hidden="true"
      style={{ position: "absolute", width: 0, height: 0, overflow: "hidden" }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
