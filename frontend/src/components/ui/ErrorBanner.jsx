/**
 * Banner de error global — se muestra arriba de la página.
 * Usado para errores de rate limiting (429) y errores de conexión.
 * Fiel al mockup: fondo error-container, ícono warning, botón cerrar.
 */
const ErrorBanner = ({ message, onDismiss }) => {
  if (!message) return null;
 
  return (
    <div className="relative z-50 w-full bg-error-container text-on-error-container py-3 px-6 flex items-center justify-center gap-2">
      <span className="material-symbols-outlined text-[20px]">warning</span>
      <p className="font-semibold text-sm">{message}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="ml-auto text-on-error-container/70 hover:text-on-error-container"
          aria-label="Cerrar mensaje de error"
        >
          <span className="material-symbols-outlined">close</span>
        </button>
      )}
    </div>
  );
};
 
export default ErrorBanner;
