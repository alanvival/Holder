import { useState } from 'react';
import { AssistenteConsultas } from './components/AssistenteConsultas/AssistenteConsultas.jsx';
import { AdminPerguntas } from './components/Admin/AdminPerguntas.jsx';
import { TenantProvider } from './context/TenantContext.jsx';

// "App já existente da Globalsys" simulado, só pra demonstrar o widget
// embutido — em produção o <AssistenteConsultas /> é importado dentro do
// app real, sem esse shell. O projeto não tem React Router configurado
// ainda, então a navegação entre Dashboard/Administração é um estado local
// simples — trocar por rotas de verdade quando o roteador entrar.
export function App() {
  const [tela, setTela] = useState('dashboard');

  return (
    <TenantProvider>
      <div style={{ minHeight: '100vh', background: '#FAF9F5' }}>
        <header
          style={{
            background:
              'linear-gradient(112.61deg, #041833 0%, #0000AA 24%, #1D1DDB 62%, #0F0FC3 81%, #00083D 100%)',
            height: 64,
            padding: '0 40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            color: '#FFFFFF',
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 600,
          }}
        >
          <span>Holder</span>
          <nav style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={() => setTela('dashboard')} style={navButtonStyle(tela === 'dashboard')}>
              Dashboard
            </button>
            <button type="button" onClick={() => setTela('admin')} style={navButtonStyle(tela === 'admin')}>
              Administração
            </button>
          </nav>
        </header>

        {tela === 'dashboard' ? (
          <main style={{ padding: 40 }}>
            <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#000A1E' }}>
              Dashboard (placeholder)
            </h1>
            <p style={{ color: 'rgba(0,10,30,0.65)', maxWidth: 480 }}>
              Conteúdo do app principal. O Assistente de Consultas fica ancorado
              no canto inferior direito, independente desta tela.
            </p>
          </main>
        ) : (
          <AdminPerguntas />
        )}

        <AssistenteConsultas />
      </div>
    </TenantProvider>
  );
}

function navButtonStyle(ativo) {
  return {
    background: ativo ? 'rgba(255,255,255,0.18)' : 'transparent',
    border: 'none',
    borderRadius: 50,
    padding: '8px 16px',
    color: '#FFFFFF',
    fontFamily: "'Space Grotesk', sans-serif",
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
  };
}
