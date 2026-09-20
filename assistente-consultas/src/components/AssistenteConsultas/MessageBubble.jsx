import { SparkleIcon, CalendarIcon, CheckIcon, AlertIcon, DownloadIcon } from './icons/index.jsx';
import { exportarRespostaComoPdf } from '../../utils/exportarPdf.js';

export function MessageBubble({ mensagem, onConfirmarSugestao, onDispensarSugestao }) {
  if (mensagem.autor === 'usuario') {
    return (
      <div className="ac-message-row ac-message-row--user">
        <div className="ac-bubble ac-bubble--user">{mensagem.texto}</div>
      </div>
    );
  }

  const isNotFound = mensagem.payload.kind === 'not_found';

  return (
    <div className="ac-message-row">
      <span className="ac-message-row__avatar">
        <SparkleIcon size={13} color="#FFFFFF" />
      </span>
      <div className="ac-bubble ac-bubble--assistant">
        {mensagem.payload.kind === 'text' && <div>{mensagem.payload.text}</div>}
        {mensagem.payload.kind === 'date' && (
          <>
            <div>{mensagem.payload.text}</div>
            <div className="ac-answer-highlight">
              <CalendarIcon />
              <span className="ac-answer-highlight__value">{mensagem.payload.date}</span>
            </div>
          </>
        )}
        {mensagem.payload.kind === 'location' && (
          <>
            <div>{mensagem.payload.text}</div>
            <div className="ac-answer-highlight">
              <span className="ac-answer-highlight__value">{mensagem.payload.local}</span>
            </div>
          </>
        )}
        {mensagem.payload.kind === 'list' && (
          <>
            <div>{mensagem.payload.text}</div>
            <div className="ac-answer-list">
              {mensagem.payload.items.map((item, index) => (
                <div className="ac-answer-list__item" key={`${mensagem.id}-item-${index}`}>
                  <CheckIcon />
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
            {mensagem.payload.contexto && <div className="ac-answer-contexto">{mensagem.payload.contexto}</div>}
          </>
        )}
        {mensagem.payload.kind === 'table' && (
          <>
            <div>{mensagem.payload.text}</div>
            <div className="ac-answer-table-wrap">
              <table className="ac-answer-table">
                <thead>
                  <tr>
                    {mensagem.payload.colunas.map((coluna) => (
                      <th key={coluna}>{coluna}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {mensagem.payload.linhas.map((linha, index) => (
                    <tr key={`${mensagem.id}-row-${index}`}>
                      {mensagem.payload.colunas.map((coluna) => (
                        <td key={coluna}>{linha[coluna] ?? '—'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {mensagem.payload.contexto && <div className="ac-answer-contexto">{mensagem.payload.contexto}</div>}
            <button
              type="button"
              className="ac-export-btn"
              onClick={() => exportarRespostaComoPdf(mensagem, { tituloRelatorio: mensagem.payload.text })}
            >
              <DownloadIcon /> Exportar PDF
            </button>
          </>
        )}
        {mensagem.payload.kind === 'metric' && (
          <>
            <div>{mensagem.payload.text}</div>
            <div className="ac-answer-highlight">
              <span className="ac-answer-highlight__value">{mensagem.payload.valor}</span>
            </div>
            {mensagem.payload.contexto && <div className="ac-answer-contexto">{mensagem.payload.contexto}</div>}
          </>
        )}
        {mensagem.origem === 'ia' && !isNotFound && (
          <div className="ac-origem-ia">
            <SparkleIcon size={10} color="#0156FC" /> Respondido pela IA — fora do catálogo padrão
          </div>
        )}
        {isNotFound && (
          <>
            <div className="ac-not-found__header">
              <AlertIcon />
              <div>Não encontrei essa informação nos registros disponíveis.</div>
            </div>
            {mensagem.sugestaoStatus === 'pendente' && (
              <>
                <div className="ac-not-found__prompt">
                  Gostaria de deixar uma sugestão para que essa consulta seja adicionada ao sistema?
                </div>
                <div className="ac-not-found__actions">
                  <button
                    type="button"
                    className="ac-btn ac-btn--primary"
                    onClick={() => onConfirmarSugestao(mensagem.id, mensagem.perguntaOrigem)}
                  >
                    Sim, sugerir
                  </button>
                  <button
                    type="button"
                    className="ac-btn ac-btn--outline"
                    onClick={() => onDispensarSugestao(mensagem.id)}
                  >
                    Agora não
                  </button>
                </div>
              </>
            )}
            {mensagem.sugestaoStatus === 'enviada' && (
              <div className="ac-not-found__prompt">Sugestão registrada — obrigado!</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
