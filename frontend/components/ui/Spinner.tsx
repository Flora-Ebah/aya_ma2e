type Props = {
  size?: number;
  className?: string;
  label?: string;
};

/** Indicateur de chargement (`sa-spinner`). */
export function Spinner({ size = 20, className = "", label = "Chargement" }: Props) {
  return (
    <span
      role="status"
      aria-label={label}
      className={`sa-spinner ${className}`.trim()}
      style={{ width: size, height: size }}
    />
  );
}
