import { useState } from 'react';
import { AssistenteConsultas } from './components/AssistenteConsultas/AssistenteConsultas.jsx';
import { AdminPerguntas } from './components/Admin/AdminPerguntas.jsx';
import { TenantProvider } from './context/TenantContext.jsx';

// URL do dashboard Streamlit (app.py, lendo do SQL Server) — embutido via
// iframe na aba "Dashboard" em vez de portado pra componentes React: mais
// rápido de entregar, e o Streamlit continua sendo a única fonte do
// dashboard (sem duas implementações pra manter sincronizadas). Rodar com
// `python -m streamlit run app.py` antes de abrir esta tela.
const DASHBOARD_URL = import.meta.env.VITE_DASHBOARD_URL ?? 'http://localhost:8501';

// "App já existente da Globalsys" simulado, só pra demonstrar o widget
// embutido — em produção o <AssistenteConsultas /> é importado dentro do
// app real, sem esse shell. O projeto não tem React Router configurado
// ainda, então a navegação entre Dashboard/Administração é um estado local
// simples — trocar por rotas de verdade quando o roteador entrar.
export function App() {
  const [tela, setTela] = useState('dashboard');

  return (
    <TenantProvider>
      <div style={{ minHeight: '100vh', background: 'var(--gs-bg-alt)' }}>
        <header
          style={{
            background: 'var(--gs-gradient-brand)',
            height: 72,
            padding: '0 40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 4px 16px rgba(0, 10, 44, 0.18)',
            position: 'relative',
            zIndex: 1,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              aria-hidden="true"
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: 'var(--gs-gradient-cta)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: 'var(--gs-font-heading)',
                fontWeight: 700,
                fontSize: 17,
                color: 'var(--gs-white)',
                flexShrink: 0,
              }}
            >
              H
            </div>
            <div>
              <div style={{ fontFamily: 'var(--gs-font-heading)', fontWeight: 700, fontSize: 17, color: 'var(--gs-white)', lineHeight: 1.15 }}>
                Holder
              </div>
              <div style={{ fontFamily: 'var(--gs-font-body)', fontWeight: 400, fontSize: 12, color: 'rgba(255,255,255,0.65)', marginTop: 1 }}>
                Customer Success
              </div>
            </div>
          </div>
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
          <main style={{ height: 'calc(100vh - 72px)' }}>
            <iframe
              src={DASHBOARD_URL}
              title="Dashboard Executivo CS"
              style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
            />
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
    border: ativo ? '1px solid rgba(255,255,255,0.3)' : '1px solid transparent',
    borderRadius: 'var(--gs-radius-pill)',
    padding: '8px 18px',
    color: 'var(--gs-white)',
    fontFamily: 'var(--gs-font-heading)',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
    transition: 'background 0.15s ease',
  };
}
