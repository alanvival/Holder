// Testa o CATÁLOGO de intenções — a parte do motor que o
// `testar-metricas.mjs` não cobre: ele confere números, este confere se as
// intenções estão sequer montadas e se casam com uma pergunta.
//
// Existe por causa de um erro concreto: uma renomeação deixou
// `resolver: clientesEmRiscoAlto` apontando pra um identificador que não
// existia mais, e isso passou por `npm run build` sem um aviso — referência
// indefinida só falha em RUNTIME, não no bundle. O sintoma era um
// ReferenceError no navegador, na hora em que alguém fizesse a pergunta.
//
// Uso: node scripts/testar-catalogo.mjs   (ou `npm run test:catalogo`)

import { intentRegistry } from '../src/engine/intentRegistry.js';
import { interpretarPergunta } from '../src/engine/matchIntent.js';

let falhas = 0;

function checar(descricao, condicao, detalhe = '') {
  if (condicao) {
    console.log(`OK   ${descricao}`);
  } else {
    falhas += 1;
    console.error(`FALHA ${descricao}${detalhe ? ` — ${detalhe}` : ''}`);
  }
}

// 1. Toda intenção precisa ter resolver CHAMÁVEL. É isto que pega
//    `resolver: nomeQueNaoExisteMais` — em módulo ESM, uma referência a
//    identificador inexistente vira ReferenceError na avaliação do módulo,
//    e se for `undefined` cai aqui.
for (const intent of intentRegistry) {
  checar(
    `intenção '${intent.id}' tem resolver chamável`,
    typeof intent.resolver === 'function',
    `resolver é ${typeof intent.resolver}`,
  );
  checar(
    `intenção '${intent.id}' tem exemplos`,
    Array.isArray(intent.exemplos) && intent.exemplos.length > 0,
  );
}

// 2. Ids únicos — id duplicado faz o casamento por similaridade devolver a
//    intenção errada de forma silenciosa.
const ids = intentRegistry.map((i) => i.id);
const duplicados = ids.filter((id, i) => ids.indexOf(id) !== i);
checar('nenhum id de intenção duplicado', duplicados.length === 0, duplicados.join(', '));

// 3. Fim a fim: cada exemplo curado de cada intenção precisa ser respondido
//    sem exceção. É o caminho que o navegador percorre de verdade.
for (const intent of intentRegistry) {
  const exemplo = intent.exemplos[0];
  if (!exemplo) continue;
  let resposta;
  try {
    resposta = interpretarPergunta(exemplo);
  } catch (erro) {
    falhas += 1;
    console.error(`FALHA '${intent.id}': "${exemplo}" levantou ${erro.name}: ${erro.message}`);
    continue;
  }
  checar(
    `'${intent.id}': primeiro exemplo é respondido`,
    resposta && resposta.encontrado !== false,
    `resposta: ${JSON.stringify(resposta)?.slice(0, 120)}`,
  );
}

console.log(`\n${intentRegistry.length} intenções verificadas, ${falhas} falha(s).`);
if (falhas > 0) process.exit(1);
