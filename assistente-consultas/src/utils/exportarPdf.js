import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

// Tokens da Globalsys (ver design-tokens.md na raiz do repo) — replicados
// aqui em RGB porque jsPDF não lê CSS custom properties.
const COR_NAVY = [4, 24, 51]; // #041833
const COR_BLUE_ACCENT = [1, 86, 252]; // #0156FC
const COR_TEXTO = [0, 10, 30]; // #000A1E
const COR_TEXTO_SUAVE = [110, 118, 133];
const COR_BORDA = [230, 233, 240];

/**
 * Exporta a resposta de uma mensagem do assistente (texto + tabela, quando
 * houver) como PDF com a identidade visual da Globalsys — cabeçalho de
 * marca, título, data de geração e o universo considerado (nunca gera
 * número novo: só formata o que a mensagem já mostrou na tela).
 */
export function exportarRespostaComoPdf(mensagem, { tituloRelatorio } = {}) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const largura = doc.internal.pageSize.getWidth();
  const margem = 40;

  // --- Cabeçalho de marca ---
  doc.setFillColor(...COR_NAVY);
  doc.rect(0, 0, largura, 70, 'F');
  doc.setFillColor(...COR_BLUE_ACCENT);
  doc.rect(0, 66, largura, 4, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.text('Holder', margem, 32);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.text('Assistente de Consultas Preditivo — relatório exportado', margem, 50);

  // --- Metadados ---
  let y = 96;
  doc.setTextColor(...COR_TEXTO_SUAVE);
  doc.setFontSize(9);
  const agora = new Date();
  doc.text(`Gerado em ${agora.toLocaleDateString('pt-BR')} às ${agora.toLocaleTimeString('pt-BR')}`, margem, y);
  y += 24;

  // --- Título do relatório (o rótulo da própria pergunta/resposta) ---
  if (tituloRelatorio) {
    doc.setTextColor(...COR_TEXTO);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    const linhasTitulo = doc.splitTextToSize(tituloRelatorio, largura - margem * 2);
    doc.text(linhasTitulo, margem, y);
    y += linhasTitulo.length * 16 + 8;
  }

  // --- Texto da resposta (o mesmo texto que já apareceu no chat) ---
  const texto = mensagem.payload?.text;
  if (texto) {
    doc.setTextColor(...COR_TEXTO);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10.5);
    const linhasTexto = doc.splitTextToSize(texto, largura - margem * 2);
    doc.text(linhasTexto, margem, y);
    y += linhasTexto.length * 14 + 16;
  }

  // --- Tabela (quando a resposta tiver colunas/linhas) ---
  const tabela = mensagem.payload?.kind === 'table' ? mensagem.payload : null;
  if (tabela?.colunas?.length) {
    autoTable(doc, {
      startY: y,
      margin: { left: margem, right: margem },
      head: [tabela.colunas],
      body: tabela.linhas.map((linha) => tabela.colunas.map((coluna) => linha[coluna] ?? '—')),
      styles: { font: 'helvetica', fontSize: 9, textColor: COR_TEXTO, lineColor: COR_BORDA, lineWidth: 0.5 },
      headStyles: { fillColor: COR_BLUE_ACCENT, textColor: [255, 255, 255], fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [250, 249, 245] }, // --gs-bg-alt
    });
    y = doc.lastAutoTable.finalY + 20;
  }

  if (mensagem.payload?.contexto) {
    doc.setTextColor(...COR_TEXTO_SUAVE);
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(9);
    const linhasContexto = doc.splitTextToSize(mensagem.payload.contexto, largura - margem * 2);
    doc.text(linhasContexto, margem, y);
  }

  // --- Rodapé em todas as páginas ---
  const totalPaginas = doc.internal.getNumberOfPages();
  for (let pagina = 1; pagina <= totalPaginas; pagina += 1) {
    doc.setPage(pagina);
    const alturaPagina = doc.internal.pageSize.getHeight();
    doc.setDrawColor(...COR_BORDA);
    doc.line(margem, alturaPagina - 36, largura - margem, alturaPagina - 36);
    doc.setTextColor(...COR_TEXTO_SUAVE);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.text('Gerado automaticamente pelo Assistente de Consultas Preditivo — Holder', margem, alturaPagina - 22);
    doc.text(`Página ${pagina} de ${totalPaginas}`, largura - margem, alturaPagina - 22, { align: 'right' });
  }

  const nomeArquivo = `holder-relatorio-${agora.toISOString().slice(0, 10)}-${Date.now().toString().slice(-5)}.pdf`;
  doc.save(nomeArquivo);
}
