# 09 — `interface-web/`

Status: aberto
Fase: 9 de 10 · Bloqueado por: 08

## Por que renomear

`assistente-consultas/` não é mais o widget: é o **shell da aplicação inteira** — header,
navegação, `<iframe>` do dashboard (`App.jsx:50-54`) e tela de admin. O assistente é **um**
componente dentro dela. Numa apresentação para banca, o nome atual gera pergunta ruim.

## Entregas

- `assistente-consultas/` → `interface-web/` (decisão Q24=b, coerente com PT-BR).
- Atualizar o caminho de escrita dos JSON em `scripts/gerar_dados_inovaapps.py:17`.
- `.env.example` próprio do front (`VITE_BACKEND_URL`, `VITE_DASHBOARD_URL`) — hoje não existe
  `.env` dentro do projeto do front, e o Vite não lê o `.env` da raiz.
- **Porta do CORS alinhada em 5173** (decisão Q30.1): o Vite sobe na 5173 por padrão e o
  README do front já diz 5173; hoje o Flask libera 5183 (`server.py:33`, `.env.example:7`) e
  rejeita o front. Mexer no backend, não no Vite.
- Garantir que nada do `tokens.css` regrediu — ele está hoje 100% conforme ao
  `design-tokens.md` (11 cores, 2 gradientes, 2 fontes, 2 raios) e assim deve continuar.

## Verificação

`npm run build` + app abrindo com o iframe do dashboard + widget respondendo + `test_tokens.py`.
