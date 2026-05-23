/**
 * Indicador visual de fortaleza de contraseña.
 * Fiel al mockup: 4 segmentos, colores del design system Struktura.
 * La validación real la hace el backend — esto es solo feedback visual.
 */
const SEGMENTS = [
  { min: 1, color: "#ffb4ab", label: null },
  { min: 2, color: "#da7726", label: null },
  { min: 3, color: "#f6ba8b", label: null },
  { min: 4, color: "#4cd7f2", label: null },
];
 
const LABELS = ["", "Muy débil", "Débil", "Fuerte", "Excelente"];
 
export const getPasswordScore = (val) => {
  if (!val) return 0;
  let score = 0;
  if (val.length > 5) score++;
  if (val.length > 8) score++;
  if (/[A-Z]/.test(val) && /[0-9]/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;
  return score;
};
 
const StrengthMeter = ({ value }) => {
  const score = getPasswordScore(value);
 
  const getSegmentColor = (index) => {
    if (!value || score === 0) return "#333538";
    if (score >= 4) return "#4cd7f2";
    if (score >= 3 && index < 3) return "#f6ba8b";
    if (score >= 2 && index < 2) return "#da7726";
    if (score >= 1 && index === 0) return "#ffb4ab";
    return "#333538";
  };
 
  return (
    <div className="mt-2">
      <div className="flex gap-1.5 px-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="flex-1 h-1 rounded-full transition-colors duration-300"
            style={{ backgroundColor: getSegmentColor(i) }}
          />
        ))}
      </div>
      <p className="text-[11px] font-medium text-on-surface-variant/60 ml-1 mt-1 h-4">
        {value ? LABELS[score] || "Excelente" : "Usa al menos 8 caracteres con símbolos."}
      </p>
    </div>
  );
};
 
export default StrengthMeter;
