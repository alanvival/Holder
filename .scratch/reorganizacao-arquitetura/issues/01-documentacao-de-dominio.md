# 01 — Documentação de domínio

Status: resolvido (commit `bf03c3a`)
Fase: 1 de 10 · Zero mudança de código

## Objetivo

Registrar o vocabulário e as decisões antes de mover qualquer arquivo, para que as 9 fases
seguintes tenham um alvo escrito.

## Entregas

- `CONTEXT.md` na raiz — glossário do domínio (sem detalhe de implementação, sem caminho de
  arquivo, sem nome de tabela).
- `docs/adr/0001-dois-conceitos-de-risco.md`
- `docs/adr/0002-porta-de-dados-com-dois-adaptadores.md`
- `docs/adr/0003-resolvedor-de-metricas-duplicado-de-proposito.md`
- `contexto_do_desafio_inovaapps_2026.md` → `docs/desafio/`
- `design-tokens.md` → `docs/`
- Corrigir os comentários que apontam para "`design-tokens.md` na raiz do repo":
  `app.py:15-18`, `.streamlit/config.toml:1-2` e `:20`.

## Deliberadamente fora desta fase

- A seção "Cores semânticas" do `design-tokens.md` entra na fase 8, junto com o código que a
  consome — doc e consumo landam no mesmo commit.
- O `README.md` real é a fase 10: escrito agora, nasceria descrevendo comandos que ainda não
  existem.

## Verificação

Nenhum código mudou além de 3 comentários. `pytest` ainda não existe nesta fase; rodar as 4
suítes atuais pelos comandos antigos para confirmar que seguem passando.
