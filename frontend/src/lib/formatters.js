/**
 * formatters.js
 * Utilidades de formato para el panel de usuarios
 */

/**
 * Formatea una fecha ISO 8601 en tiempo relativo en español
 * Ej: "Hace 2 horas", "Hace 14 días", "Hace 5 meses"
 */
export function formatRelativeTime(isoString) {
  if (!isoString) return '—';
  const date  = new Date(isoString);
  const now   = new Date();
  const diffMs = now - date;
  const diffSec  = Math.floor(diffMs / 1000);
  const diffMin  = Math.floor(diffSec / 60);
  const diffHr   = Math.floor(diffMin / 60);
  const diffDay  = Math.floor(diffHr  / 24);
  const diffMo   = Math.floor(diffDay / 30);
  const diffYr   = Math.floor(diffDay / 365);

  if (diffSec  < 60)   return 'Justo ahora';
  if (diffMin  < 60)   return `Hace ${diffMin} ${diffMin === 1 ? 'minuto' : 'minutos'}`;
  if (diffHr   < 24)   return `Hace ${diffHr} ${diffHr === 1 ? 'hora' : 'horas'}`;
  if (diffDay  < 30)   return `Hace ${diffDay} ${diffDay === 1 ? 'día' : 'días'}`;
  if (diffMo   < 12)   return `Hace ${diffMo} ${diffMo === 1 ? 'mes' : 'meses'}`;
  return `Hace ${diffYr} ${diffYr === 1 ? 'año' : 'años'}`;
}