import { SparkleIcon, ChevronDownIcon } from './icons/index.jsx';

export function PanelHeader({ onClose }) {
  return (
    <div className="ac-panel__header">
      <div className="ac-panel__header-left">
        <span className="ac-panel__avatar">
          <SparkleIcon size={18} color="#FFFFFF" />
        </span>
        <span>
          <div className="ac-panel__title">Assistente de Consultas</div>
          <div className="ac-panel__subtitle">Pergunte sobre seus dados</div>
        </span>
      </div>
      <button type="button" className="ac-panel__close" onClick={onClose} aria-label="Minimizar">
        <ChevronDownIcon />
      </button>
    </div>
  );
}
