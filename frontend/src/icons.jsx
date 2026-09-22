/* Small hand-drawn icon set. The heartbeat trace is the brand motif,
   reused in the logo, the loading state, and nowhere else. */

export function BrandMark({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="9" fill="#7C5CFF" />
      <path
        d="M4 17h4.4l2-5.6 3.6 11.2 2.6-8.4 1.8 4.6L20 17h2.4"
        stroke="#0A0E1F"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M20 17h4l1.6-3"
        stroke="#0A0E1F"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function EkgTrace() {
  return (
    <svg viewBox="0 0 200 34" fill="none">
      <path
        d="M0 17 H14 L20 6 L28 30 L34 17 H48 L54 22 L60 12 L66 17 H84 L90 6 L98 30 L104 17 H118 L124 22 L130 12 L136 17 H154 L160 6 L168 30 L174 17 H188 L194 22 L200 12"
        stroke="#40C7FF"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function UploadIcon() {
  return (
    <svg width="46" height="46" viewBox="0 0 46 46" fill="none" className="cloud-icon">
      <path
        d="M14 32a7 7 0 0 1-1-13.9A9 9 0 0 1 30 15a6.5 6.5 0 0 1 3 12.4"
        stroke="#7C5CFF"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path d="M23 20v13M18 27l5-5 5 5" stroke="#40C7FF" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconUpload() {
  return (
    <svg width="17" height="17" viewBox="0 0 20 20" fill="none">
      <path d="M4 13.5v1.7A1.8 1.8 0 0 0 5.8 17h8.4a1.8 1.8 0 0 0 1.8-1.8v-1.7M10 3v9m0-9L6.5 6.5M10 3l3.5 3.5"
        stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export function IconReport() {
  return (
    <svg width="17" height="17" viewBox="0 0 20 20" fill="none">
      <path d="M5 2.5h7l3.5 3.5V17a.5.5 0 0 1-.5.5H5a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5Z"
        stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" fill="none" />
      <path d="M7 10.5h6M7 13.5h6M7 7.5h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function IconChevron() {
  return (
    <svg className="chev" width="14" height="14" viewBox="0 0 16 16" fill="none">
      <path d="M6 3.5 11 8l-5 4.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}
