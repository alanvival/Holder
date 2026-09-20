import { useId, useState } from 'react';
import { PaperPlaneIcon } from './icons/index.jsx';

export function Composer({ onEnviar, desabilitado }) {
  const [valor, setValor] = useState('');
  const inputId = useId();

  const enviar = () => {
    if (!valor.trim() || desabilitado) return;
    onEnviar(valor);
    setValor('');
  };

  return (
    <div className="ac-panel__composer">
      <label htmlFor={inputId} className="sr-only">
        Digite sua pergunta
      </label>
      <input
        id={inputId}
        type="text"
        className="ac-composer__input"
        placeholder="Pergunte alguma coisa..."
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') enviar();
        }}
        disabled={desabilitado}
      />
      <button
        type="button"
        className="ac-composer__send"
        aria-label="Enviar pergunta"
        onClick={enviar}
        disabled={desabilitado || !valor.trim()}
      >
        <PaperPlaneIcon />
      </button>
    </div>
  );
}
