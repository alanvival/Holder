// Base mock — representa os dados "já cadastrados no sistema" que o motor
// de intenções consulta. Numa integração real, isso vira chamadas à API/CRM
// da Globalsys; a forma dos dados (pessoa, acompanhamento, atividade,
// procedimento, local de cadastro) é o contrato que o motor espera.

export const pessoas = [
  { id: 'p1', nome: 'João Pereira', unidade: 'Unidade Centro' },
  { id: 'p2', nome: 'Maria Souza', unidade: 'Unidade Norte' },
  { id: 'p3', nome: 'Carlos Lima', unidade: 'Unidade Sul' },
  { id: 'p4', nome: 'Ana Ribeiro', unidade: 'Unidade Centro' },
];

export const acompanhamentos = [
  { id: 'ac1', pessoaId: 'p1', data: '2026-09-12', responsavel: 'Equipe Centro' },
  { id: 'ac2', pessoaId: 'p1', data: '2026-08-03', responsavel: 'Equipe Centro' },
  { id: 'ac3', pessoaId: 'p2', data: '2026-07-20', responsavel: 'Equipe Norte' },
  { id: 'ac4', pessoaId: 'p4', data: '2026-09-01', responsavel: 'Equipe Centro' },
  // Carlos Lima (p3) não tem acompanhamento nos últimos meses — cai no
  // cenário "quem está sem acompanhamento há um período".
];

export const atividades = [
  { id: 'at1', pessoaId: 'p1', tipo: 'Acompanhamento', data: '2026-09-03' },
  { id: 'at2', pessoaId: 'p1', tipo: 'Procedimento', data: '2026-09-10' },
  { id: 'at3', pessoaId: 'p1', tipo: 'Acompanhamento', data: '2026-09-18' },
  { id: 'at4', pessoaId: 'p2', tipo: 'Procedimento', data: '2026-09-05' },
  { id: 'at5', pessoaId: 'p4', tipo: 'Acompanhamento', data: '2026-09-01' },
];

export const procedimentos = [
  { id: 'proc1', nome: 'Cadastro de novo paciente', local: 'Menu Cadastros > Novo cadastro' },
  { id: 'proc2', nome: 'Registro de acompanhamento', local: 'Ficha da pessoa > Aba Acompanhamentos > Novo' },
  { id: 'proc3', nome: 'Emissão de relatório mensal', local: 'Menu Relatórios > Relatório mensal' },
];

export const camposCadastrados = [
  { id: 'campo1', nome: 'Telefone de contato', local: 'Ficha da pessoa > Dados de contato' },
  { id: 'campo2', nome: 'Convênio', local: 'Ficha da pessoa > Dados administrativos' },
  { id: 'campo3', nome: 'Histórico de atendimentos', local: 'Ficha da pessoa > Aba Histórico' },
];

export function hojeFixo() {
  // Data de referência fixa para tornar as respostas do mock determinísticas
  // em demonstração (evita respostas que mudam conforme o dia rodado).
  return new Date('2026-09-19T12:00:00');
}
