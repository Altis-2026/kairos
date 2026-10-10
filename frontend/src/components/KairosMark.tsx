const RING_UPPER = "M 79.0 22.7 A 44 44 0 0 0 22.2 77.6";
const RING_LOWER = "M 48.9 105.3 A 44 44 0 0 0 105.8 50.4";

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
      <path d={RING_UPPER} stroke="currentColor" strokeWidth="8.5" strokeLinecap="round" />
      <path d={RING_LOWER} stroke="currentColor" strokeWidth="8.5" strokeLinecap="round" />
      <path d={TRAJECTORY} fill="currentColor" />
      <circle cx="91.7" cy="28.5" r="8" fill="currentColor" />
    </svg>
  );
}
