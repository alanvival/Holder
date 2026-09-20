import { ChatIcon } from './icons/index.jsx';

export function FAB({ onClick }) {
  return (
    <button type="button" className="ac-fab" onClick={onClick} aria-label="Abrir assistente de consultas" aria-haspopup="dialog">
      <ChatIcon size={22} color="#FFFFFF" />
    </button>
  );
}
