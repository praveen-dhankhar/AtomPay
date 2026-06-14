/**
 * AtomLoader — the signature AtomPay loading animation.
 *
 * A nucleus with three tilted orbits, each carrying an electron that
 * whirls around while something is processing. Pure CSS animation
 * (styles live in global.css). Reused for page loads, section loads,
 * buttons, and the AI "thinking" state.
 *
 * @param {number} size   diameter in px (default 64)
 * @param {string} label  optional caption shown under the atom
 */
export default function AtomLoader({ size = 64, label }) {
  return (
    <div className="atom-loader" style={{ "--atom-size": `${size}px` }}>
      <div className="atom" aria-label="loading" role="status">
        <div className="atom-nucleus" />
        <div className="atom-orbit orbit-1"><span className="atom-electron" /></div>
        <div className="atom-orbit orbit-2"><span className="atom-electron" /></div>
        <div className="atom-orbit orbit-3"><span className="atom-electron" /></div>
      </div>
      {label && <span className="atom-loader-label">{label}</span>}
    </div>
  );
}
