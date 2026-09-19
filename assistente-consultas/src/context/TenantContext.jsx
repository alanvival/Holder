import { createContext, useContext, useMemo } from 'react';

// Placeholder até o backend multi-cliente existir. Toda chamada relacionada
// ao assistente (services/assistenteApi.js) recebe esse contexto junto —
// trocar os valores fixos abaixo por dados reais de sessão/login é a única
// mudança necessária quando a autenticação real entrar.
const TenantContext = createContext({
  empresaAtual: { id: 'tenant-holder', nome: 'Holder' },
  usuarioAtual: { id: 'user-placeholder', nome: 'Usuário' },
});

export function TenantProvider({
  empresaAtual = { id: 'tenant-holder', nome: 'Holder' },
  usuarioAtual = { id: 'user-placeholder', nome: 'Usuário' },
  children,
}) {
  const value = useMemo(() => ({ empresaAtual, usuarioAtual }), [empresaAtual, usuarioAtual]);
  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenant() {
  return useContext(TenantContext);
}
