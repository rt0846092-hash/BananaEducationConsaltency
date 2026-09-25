/**
 * The mark, as inline SVG rather than an <img>. That way it inherits colour
 * from whatever it sits on — green on the white header, paper-white on the
 * navy footer — without shipping two files.
 */
export default function Logo({ className = "h-8 w-8", tile = true }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      {tile && <rect width="64" height="64" rx="14" className="fill-navy-deep" />}
      <path
        d="M17 44 A29 29 0 0 1 45 16"
        fill="none"
        strokeWidth="14"
        strokeLinecap="round"
        className="stroke-grass"
      />
    </svg>
  );
}
