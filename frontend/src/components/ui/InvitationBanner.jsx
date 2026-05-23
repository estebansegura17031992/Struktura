/**
 * Banner de invitación a proyecto.
 * Solo se renderiza cuando viene un token de invitación en la URL.
 * Fiel al mockup: fondo primary-container, ícono mail, nombre del proyecto en negrita.
 */
const InvitationBanner = ({ projectName }) => {
  if (!projectName) return null;
 
  return (
    <div className="relative z-40 w-full bg-primary-container text-on-primary-container py-3 px-6 flex items-center justify-center gap-2 border-b border-on-primary-container/10">
      <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
        mail
      </span>
      <p className="font-semibold text-sm">
        Estás siendo invitado al proyecto{" "}
        <span className="font-bold underline decoration-2 underline-offset-4">
          {projectName}
        </span>
      </p>
    </div>
  );
};
 
export default InvitationBanner;
