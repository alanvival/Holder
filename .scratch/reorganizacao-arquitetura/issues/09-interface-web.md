# 09 — `interface-web/`

Status: resolvido

## Resultado

`88 passed`, `18/18` no JS, `npm run build` passa. O `.env.example` próprio do front existe
agora — o Vite **não** lê o `.env` da raiz do repositório, e essa era uma das causas da
configuração divergente que virou o bug de CORS.

Nota sobre o rename em massa: a troca de `assistente-consultas` por `interface-web` foi feita
com `sed` em todos os arquivos, e isso trocou o nome também em texto corrido onde ele se
referia ao **passado** (docstrings e estes próprios issues). Corrigido nos pontos onde o nome
antigo era o correto, incluindo um caminho que ficou errado
(`interface-web/scripts/gerar_dados_inovaapps.py` — o script mora em `scripts/`).
Fase: 9 de 10 · Bloqueado por: 08

## Por que renomear

`assistente-consultas/` não era mais o widget: é o **shell da aplicação inteira** — header,
navegação, `<iframe>` do dashboard (`App.jsx:50-54`) e tela de admin. O assistente é **um**
componente dentro dela. Numa apresentação para banca, o nome antigo geraria pergunta ruim.

## Entregas

- `assistente-consultas/` → `interface-web/` (decisão Q24=b, coerente com PT-BR).
- Atualizar o caminho de escrita dos JSON em `scripts/gerar_dados_inovaapps.py:17`.
- `.env.example` próprio do front (`VITE_BACKEND_URL`, `VITE_DASHBOARD_URL`) — hoje não existe
  `.env` dentro do projeto do front, e o Vite não lê o `.env` da raiz.
- **Porta do CORS alinhada em 5173** (decisão Q30.1): o Vite sobe na 5173 por padrão e o
  README do front já diz 5173; hoje o Flask libera 5183 (`server.py:33`, `.env.example:7`) e
  rejeita o front. Mexer no backend, não no Vite.

  **Atenção — achado da fase 3:** o `.env` real desta máquina fixa
  `FRONTEND_ORIGIN=http://localhost:5183`. Como o `chamarBackend` devolve `null` em qualquer
  falha e cai no comportamento local, um CORS bloqueado **não aparece como erro** — só como
  assistente respondendo menos. Mas o fallback de IA comprovadamente funciona nesta máquina,
  o que significa que o front **não** está rodando na 5173 aqui. Antes de mexer, confirmar com
  o usuário como ele sobe o front; alinhar o backend em 5173 às cegas pode quebrar justamente
  o que hoje funciona.

  Correção proposta (mais forte que a original): fixar `server.port: 5173` **e**
  `strictPort: true` no `vite.config.js`, além do backend em 5173. Com `strictPort`, o Vite
  falha alto em vez de escolher outra porta em silêncio — que é o que provavelmente originou
  essa divergência.

  **RESOLVIDO e ANTECIPADO para antes da fase 4.** O usuário confirmou que sobe o front com
  `npm run dev` puro, ou seja, na 5173 — então o bug estava ativo. Provado com sonda de CORS:
  requisição com `Origin: http://localhost:5173` voltava **sem**
  `Access-Control-Allow-Origin`, o que faz o navegador descartar a resposta enquanto o Flask
  **executa** a requisição normalmente (a sonda gravou linha no histórico e devolveu 201).
  Resultado prático: o widget vinha caindo no modo local em silêncio.

  Antecipado porque a verificação visual das fases 4 a 8 inclui o chat, e não faz sentido
  pedir conferência de um chat quebrado. Depois da correção: 5173 recebe o cabeçalho, 5183
  não. O que resta desta fase é o rename para `interface-web/` e o `.env.example` próprio.
- Garantir que nada do `tokens.css` regrediu — ele está hoje 100% conforme ao
  `design-tokens.md` (11 cores, 2 gradientes, 2 fontes, 2 raios) e assim deve continuar.

## Verificação

`npm run build` + app abrindo com o iframe do dashboard + widget respondendo + `test_tokens.py`.
