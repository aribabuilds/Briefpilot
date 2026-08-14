import type { BBox } from "@/types/job";

// M18: ADR-0002's BBox is already fractional (0-1 relative to page width/
// height), so converting it to CSS positioning is direct percentage math --
// no pixel measurement, no ResizeObserver, nothing that depends on the
// image's actual rendered size. A box positioned this way stays aligned at
// any render width automatically, purely via CSS. The caller is responsible
// for wrapping the page image in a `position: relative` container that this
// style is `position: absolute`-positioned within.
export interface BBoxStyle {
  left: string;
  top: string;
  width: string;
  height: string;
}

export function bboxToStyle(bbox: BBox): BBoxStyle {
  return {
    left: `${bbox.x * 100}%`,
    top: `${bbox.y * 100}%`,
    width: `${bbox.width * 100}%`,
    height: `${bbox.height * 100}%`,
  };
}
