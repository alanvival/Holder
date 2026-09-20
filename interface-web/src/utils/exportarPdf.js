import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

// Tokens da Globalsys (ver docs/design-tokens.md) — replicados
// aqui em RGB porque jsPDF não lê CSS custom properties.
const COR_NAVY = [4, 24, 51]; // #041833
const COR_BLUE_ACCENT = [1, 86, 252]; // #0156FC
const COR_TEXTO = [0, 10, 30]; // #000A1E
const COR_TEXTO_SUAVE = [110, 118, 133];
const COR_BORDA = [230, 233, 240];

// A resposta da IA vem em markdown (**negrito**, ### título, tabelas em
// pipe) — jogar isso cru num doc.text() deixava os símbolos literais na
// tela ("**Cliente:**", "| Indicador | Valor |") em vez de formatação de
// verdade. stripBold só remove os marcadores (jsPDF com fonte padrão não
// suporta negrito inline misturado com texto normal na mesma linha sem
// trocar de fonte por trecho, o que não vale o esforço aqui).
function stripBold(texto) {
  return texto.replace(/\*\*(.*?)\*\*/g, '$1');
}

function ehLinhaTabela(linha) {
  return linha.trim().startsWith('|') && linha.trim().endsWith('|');
}

function ehSeparadorTabela(linha) {
  return /^\|?[\s:|-]+\|?$/.test(linha.trim()) && linha.includes('-');
}

function parseLinhaTabela(linha) {
  const conteudo = linha.trim().replace(/^\|/, '').replace(/\|$/, '');
  return conteudo.split('|').map((celula) => stripBold(celula.trim()));
}

// Usa a primeira linha não vazia da resposta como título curto do
// relatório — antes o título era a resposta INTEIRA de novo (duplicando o
// conteúdo: uma vez "em negrito" no topo, outra vez como corpo do texto,
// as duas cópias juntas estourando a página e se sobrepondo ao rodapé).
function tituloAPartirDoTexto(texto) {
  if (!texto) return null;
  const primeira = texto.split('\n').find((linha) => linha.trim().length > 0) || '';
  const limpa = stripBold(primeira).replace(/^#{1,6}\s*/, '').trim();
  if (!limpa) return null;
  return limpa.length > 90 ? `${limpa.slice(0, 90)}…` : limpa;
}

/**
 * Renderiza o corpo em markdown (parágrafos, ### títulos, > citações e
 * tabelas em pipe) como elementos reais do PDF, com paginação manual —
 * doc.text() sozinho não quebra página, então um texto longo (ex:
 * explicabilidade do Score de Risco) simplesmente escrevia por cima do
 * rodapé em vez de continuar numa página 2. Retorna o novo `y` depois do
 * conteúdo, pra quem chamou continuar desenhando (ex: o bloco de contexto).
 */
function renderizarMarkdown(doc, texto, { x, y, larguraUtil, alturaPagina, margem, margemInferior }) {
  const linhas = texto.split('\n');
  let cursor = y;
  let i = 0;

  function garantirEspaco(altura) {
    if (cursor + altura > alturaPagina - margemInferior) {
      doc.addPage();
      cursor = margem;
    }
  }

  while (i < linhas.length) {
    const linha = linhas[i];

    if (linha.trim() === '') {
      cursor += 8;
      i += 1;
      continue;
    }

    if (ehLinhaTabela(linha)) {
      const blocoTabela = [];
      while (i < linhas.length && ehLinhaTabela(linhas[i])) {
        blocoTabela.push(linhas[i]);
        i += 1;
      }
      const semSeparador = blocoTabela.filter((l) => !ehSeparadorTabela(l)).map(parseLinhaTabela);
      const [cabecalho, ...corpo] = semSeparador;
      if (cabecalho) {
        garantirEspaco(50);
        autoTable(doc, {
          startY: cursor,
          margin: { left: x, right: x, bottom: margemInferior },
          head: [cabecalho],
          body: corpo,
          styles: { font: 'helvetica', fontSize: 9, textColor: COR_TEXTO, lineColor: COR_BORDA, lineWidth: 0.5 },
          headStyles: { fillColor: COR_BLUE_ACCENT, textColor: [255, 255, 255], fontStyle: 'bold' },
          alternateRowStyles: { fillColor: [250, 249, 245] }, // --gs-bg-alt
        });
        cursor = doc.lastAutoTable.finalY + 16;
      }
      continue;
    }

    const heading = linha.match(/^#{1,6}\s+(.*)/);
    if (heading) {
      garantirEspaco(24);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11.5);
      doc.setTextColor(...COR_TEXTO);
      doc.text(stripBold(heading[1]), x, cursor);
      cursor += 18;
      i += 1;
      continue;
    }

    const citacao = linha.match(/^>\s?(.*)/);
    if (citacao) {
      const envolvidas = doc.splitTextToSize(stripBold(citacao[1]), larguraUtil - 16);
      for (const l of envolvidas) {
        garantirEspaco(14);
        // setFont a cada linha, não só uma vez fora do loop — ver
        // comentário no título em exportarRespostaComoPdf sobre o bug de
        // codificação em chamadas consecutivas com o mesmo estado de fonte.
        doc.setFont('helvetica', 'italic');
        doc.setFontSize(10);
        doc.setTextColor(...COR_TEXTO_SUAVE);
        doc.text(l, x + 16, cursor);
        cursor += 14;
      }
      i += 1;
      continue;
    }

    const envolvidas = doc.splitTextToSize(stripBold(linha), larguraUtil);
    for (const l of envolvidas) {
      garantirEspaco(14);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(10.5);
      doc.setTextColor(...COR_TEXTO);
      doc.text(l, x, cursor);
      cursor += 14;
    }
    i += 1;
  }

  return cursor;
}

/**
 * Exporta a resposta de uma mensagem do assistente (texto em markdown e/ou
 * tabela estruturada) como PDF com a identidade visual da Globalsys —
 * cabeçalho de marca, título curto, data de geração e o universo
 * considerado (nunca gera número novo: só formata o que a mensagem já
 * mostrou na tela). Pagina de verdade quando o conteúdo é longo.
 */
export function exportarRespostaComoPdf(mensagem) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const largura = doc.internal.pageSize.getWidth();
  const alturaPagina = doc.internal.pageSize.getHeight();
  const margem = 40;
  const margemInferior = 50;
  const larguraUtil = largura - margem * 2;

  function desenharCabecalhoMarca() {
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
  }

  desenharCabecalhoMarca();

  let y = 96;
  doc.setTextColor(...COR_TEXTO_SUAVE);
  doc.setFontSize(9);
  const agora = new Date();
  doc.text(`Gerado em ${agora.toLocaleDateString('pt-BR')} às ${agora.toLocaleTimeString('pt-BR')}`, margem, y);
  y += 24;

  const texto = mensagem.payload?.text;
  const titulo = tituloAPartirDoTexto(texto);
  if (titulo) {
    // Uma chamada por linha, com setFont/setFontSize repetidos ANTES de
    // cada uma (não só uma vez fora do loop) — jsPDF corrompe a
    // codificação de uma linha acentuada quando ela é a 2ª+ chamada de
    // texto seguida com o mesmo estado de fonte (bug observado ao vivo
    // duas vezes: só reproduz com o app rodando de verdade, nunca em
    // teste isolado — ver histórico de commit). Repetir setFont a cada
    // iteração força o estado interno a ser reconstruído, evitando o
    // gatilho — doc.text(array, x, y) sozinho não bastou.
    for (const linhaTitulo of doc.splitTextToSize(titulo, larguraUtil)) {
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.setTextColor(...COR_TEXTO);
      doc.text(linhaTitulo, margem, y);
      y += 16;
    }
    y += 12;
  }

  // A primeira linha não vazia já virou o título acima — não repete ela de
  // novo como primeira linha do corpo (senão duplica exatamente o que
  // acabou de aparecer em negrito no topo).
  if (texto) {
    const linhasTexto = texto.split('\n');
    const indicePrimeira = linhasTexto.findIndex((linha) => linha.trim().length > 0);
    const corpo = indicePrimeira >= 0 ? linhasTexto.slice(indicePrimeira + 1).join('\n') : texto;
    y = renderizarMarkdown(doc, corpo, { x: margem, y, larguraUtil, alturaPagina, margem, margemInferior });
  }

  // --- Tabela estruturada (quando a resposta tiver colunas/linhas reais,
  // além do texto em markdown acima) ---
  const tabela = mensagem.payload?.kind === 'table' ? mensagem.payload : null;
  if (tabela?.colunas?.length) {
    if (y + 50 > alturaPagina - margemInferior) {
      doc.addPage();
      y = margem;
    }
    autoTable(doc, {
      startY: y,
      margin: { left: margem, right: margem, bottom: margemInferior },
      head: [tabela.colunas],
      body: tabela.linhas.map((linha) => tabela.colunas.map((coluna) => linha[coluna] ?? '—')),
      styles: { font: 'helvetica', fontSize: 9, textColor: COR_TEXTO, lineColor: COR_BORDA, lineWidth: 0.5 },
      headStyles: { fillColor: COR_BLUE_ACCENT, textColor: [255, 255, 255], fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [250, 249, 245] }, // --gs-bg-alt
    });
    y = doc.lastAutoTable.finalY + 20;
  }

  if (mensagem.payload?.contexto) {
    if (y + 20 > alturaPagina - margemInferior) {
      doc.addPage();
      y = margem;
    }
    for (const linhaContexto of doc.splitTextToSize(mensagem.payload.contexto, larguraUtil)) {
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(9);
      doc.setTextColor(...COR_TEXTO_SUAVE);
      doc.text(linhaContexto, margem, y);
      y += 12;
    }
  }

  // --- Rodapé em todas as páginas ---
  const totalPaginas = doc.internal.getNumberOfPages();
  for (let pagina = 1; pagina <= totalPaginas; pagina += 1) {
    doc.setPage(pagina);
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
