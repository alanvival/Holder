# Assistente de Consultas — Globalsys

Widget de consulta em linguagem natural embutido em app existente. **Sem IA
generativa**: por trás, um motor de intenções determinístico interpreta a
pergunta, casa contra um dicionário de intenções cadastradas e resolve contra
dados reais — nunca gera texto livre.

## Rodando localmente

```bash
npm install
npm run dev
```

Abre em `http://localhost:5173` (ou porta seguinte livre). O `src/App.jsx` é
só um shell de demonstração simulando o app principal da Globalsys — em
produção, importe `<AssistenteConsultas />` dentro do app real.

## Estrutura

```
src/
  components/AssistenteConsultas/   # UI: FAB, painel, bolhas, estados
    icons/                          # SVGs inline (sem biblioteca de ícones)
  engine/                           # motor de interpretação (desacoplado da UI)
    similarity.js                   # comparação tolerante a variações de escrita
    entities.js                     # extração de pessoa/data/período do texto
    intentRegistry.js               # "dicionário" de intenções cadastradas
    matchIntent.js                  # orquestra extração + match + resolução
    suggestionsStore.js             # sugestões de usuários pendentes de análise
    responseFormat.js               # formatos de resposta estruturada
  data/
    mockDatabase.js                 # dados mock (troque por API/CRM real)
    suggestedQuestions.js           # chips de sugestão, lidos do intentRegistry
  hooks/useAssistant.js             # estado da conversa (sessão, histórico)
```

## Estados implementados

Fechado (FAB + bolha) · Aberto/vazio (sugestões) · Digitando pergunta ·
Carregando resposta ("Consultando os registros...") · Resposta organizada
(texto, data em destaque, lista, local) · Sem resultado + fluxo de sugestão ·
Erro de sistema (estado adicional exigido pela especificação, ausente no
protótipo original).

## Motor de interpretação — como estender

Cadastrar uma nova pergunta é adicionar uma entrada em
`src/engine/intentRegistry.js`: um `id`, frases de exemplo (`exemplos`) para
o matcher por similaridade, quais entidades ela precisa (`requerEntidade`) e
um `resolver(entidades, hoje)` que consulta os dados e devolve um payload de
`src/engine/responseFormat.js`. Isso é a "camada de gestão de perguntas"
citada na especificação — hoje é código, mas a estrutura de dados já está
pronta para virar uma tela de admin ligada a um backend real.

## Identidade visual — regras pra não regredir

Toda cor, fonte, raio e sombra vem de `src/styles/tokens.css` (nunca um
valor solto direto no componente — se falta um token pro que a tela
precisa, o token é o que falta, não uma exceção). Ver `design-tokens.md`
na raiz do repo pra fonte da marca. Proibido em qualquer tela nova (tiques
clássicos de interface gerada por IA sem checar a marca do cliente):

- Gradiente roxo/rosa/magenta (`#8B5CF6`→`#EC4899` ou variantes) — a marca
  usa `--gs-gradient-brand`/`--gs-gradient-cta`, nunca violeta.
- Ícone de sparkle/estrelinha (✨) ou robô/cérebro/lâmpada como indicador de
  "isto é IA" — o widget usa `ChatIcon` (balão de chat), sempre.
- Fonte Inter, system-ui ou sans-serif genérica renderizando de verdade —
  só Space Grotesk (`--gs-font-heading`) e Montserrat (`--gs-font-body`).
- Sombra colorida com efeito "glow" — sombras usam `rgba(0,10,44,α)`
  neutro (`--ac-shadow-*`), nunca cor saturada.
- Emoji decorativo em label/título/mensagem de sistema (fora de copy já
  aprovada) e blob/mancha gradiente de fundo — nenhum dos dois.
- Border-radius fora de `--gs-radius-card` (20px) / `--gs-radius-pill`
  (50px) / `--gs-radius-bubble` (18px, só balão de chat) /
  `--gs-radius-chip` (12px) / `50%`-`100%` (elementos circulares).

## Pendências conhecidas (fora do escopo deste scaffold)

- Persistência de histórico por usuário (hoje só em memória/sessão).
- Tela de administração (cadastro de intenções, revisão de sugestões) — a
  estrutura de dados já suporta, falta a UI.
- Testado manualmente no Chrome (estados 1–4 batendo com o protótipo,
  responsivo mobile não pôde ser verificado ao vivo nesta sessão por
  limitação da janela do browser automatizado — a regra CSS `@media
  (max-width: 480px)` segue o padrão do protótipo e deve ser conferida em
  device real antes do merge).
