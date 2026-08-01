/**
 * The Kairos mark: an orbital ring broken by a satellite's trajectory, with the
 * satellite riding in the upper break.
 *
 * Inline SVG rather than a PNG so it stays crisp at every size (favicon through
 * hero), follows `currentColor` with the theme, and costs no extra request on
 * first paint. The ring is two arcs with deliberate gaps on the trajectory's
 * axis, so the sweep reads as passing through the orbit rather than sitting on
 * top of it.
 */

const RING_UPPER = "M 79.0 22.7 A 44 44 0 0 0 22.2 77.6";
const RING_LOWER = "M 48.9 105.3 A 44 44 0 0 0 105.8 50.4";
// A lens tapered to points at both ends, on the same 30-degree axis as the gaps.
const TRAJECTORY = "M 1.6 100 Q 68.5 71.8 126.4 28 Q 59.5 56.2 1.6 100 Z";

export default function KairosMark({
  size = 36,
  className = "",
  title,
}: {
  size?: number;
  className?: string;
  title?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 128 128"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role={title ? "img" : "presentation"}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      {title ? <title>{title}</title> : null}
      <path
        d={RING_UPPER}
        stroke="currentColor"
        strokeWidth="8.5"
        strokeLinecap="round"
      />
      <path
        d={RING_LOWER}
        stroke="currentColor"
        strokeWidth="8.5"
        strokeLinecap="round"
      />
      <path d={TRAJECTORY} fill="currentColor" />
      <circle cx="91.7" cy="28.5" r="8" fill="currentColor" />
    </svg>
  );
}
