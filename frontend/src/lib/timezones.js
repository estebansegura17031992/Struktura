/**
 * Lista de timezones IANA agrupadas por región.
 * Formato: { label: "America/Mexico_City (GMT-6)", value: "America/Mexico_City" }
 * Se usa en el selector de timezone del perfil.
 */
export const TIMEZONES = [
  { value: "UTC",                      label: "UTC (GMT+0)" },
  { value: "America/Mexico_City",      label: "America/Mexico_City (GMT-6)" },
  { value: "America/Monterrey",        label: "America/Monterrey (GMT-6)" },
  { value: "America/Cancun",           label: "America/Cancun (GMT-5)" },
  { value: "America/New_York",         label: "America/New_York (GMT-5)" },
  { value: "America/Chicago",          label: "America/Chicago (GMT-6)" },
  { value: "America/Denver",           label: "America/Denver (GMT-7)" },
  { value: "America/Los_Angeles",      label: "America/Los_Angeles (GMT-8)" },
  { value: "America/Bogota",           label: "America/Bogota (GMT-5)" },
  { value: "America/Lima",             label: "America/Lima (GMT-5)" },
  { value: "America/Santiago",         label: "America/Santiago (GMT-4)" },
  { value: "America/Buenos_Aires",     label: "America/Argentina/Buenos_Aires (GMT-3)" },
  { value: "America/Sao_Paulo",        label: "America/Sao_Paulo (GMT-3)" },
  { value: "Europe/London",            label: "Europe/London (GMT+0)" },
  { value: "Europe/Madrid",            label: "Europe/Madrid (GMT+1)" },
  { value: "Europe/Paris",             label: "Europe/Paris (GMT+1)" },
  { value: "Europe/Berlin",            label: "Europe/Berlin (GMT+1)" },
  { value: "Europe/Moscow",            label: "Europe/Moscow (GMT+3)" },
  { value: "Asia/Dubai",               label: "Asia/Dubai (GMT+4)" },
  { value: "Asia/Kolkata",             label: "Asia/Kolkata (GMT+5:30)" },
  { value: "Asia/Singapore",           label: "Asia/Singapore (GMT+8)" },
  { value: "Asia/Tokyo",               label: "Asia/Tokyo (GMT+9)" },
  { value: "Asia/Shanghai",            label: "Asia/Shanghai (GMT+8)" },
  { value: "Australia/Sydney",         label: "Australia/Sydney (GMT+10)" },
  { value: "Pacific/Auckland",         label: "Pacific/Auckland (GMT+12)" },
  { value: "Africa/Cairo",             label: "Africa/Cairo (GMT+2)" },
  { value: "Africa/Lagos",             label: "Africa/Lagos (GMT+1)" },
];
 
/** Detecta la timezone actual del navegador y la busca en la lista. */
export const detectCurrentTimezone = () => {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const found = TIMEZONES.find((t) => t.value === tz);
    return found ? tz : "UTC";
  } catch {
    return "UTC";
  }
};
 
/** Busca el label de una timezone por su value. */
export const getTimezoneLabel = (value) => {
  const found = TIMEZONES.find((t) => t.value === value);
  return found ? found.label : value;
};
