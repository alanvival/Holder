export function SuggestedQuestions({ perguntas, onSelecionar }) {
  if (perguntas.length === 0) return null;
  return (
    <div className="ac-suggestions">
      <div className="ac-suggestions__label">Perguntas frequentes</div>
      {perguntas.map((pergunta) => (
        <button
          key={pergunta.id}
          type="button"
          className="ac-suggestion-chip"
          onClick={() => onSelecionar(pergunta.texto)}
        >
          {pergunta.texto}
        </button>
      ))}
    </div>
  );
}
