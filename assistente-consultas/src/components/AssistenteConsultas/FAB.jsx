import { SparkleIcon } from './icons/index.jsx';

export function FAB({ onClick }) {
  return (
    <button type="button" className="ac-fab" onClick={onClick} aria-label="Abrir assistente de consultas" aria-haspopup="dialog">
      <SparkleIcon size={28} color="#FFFFFF" />
    </button>
  );
}
