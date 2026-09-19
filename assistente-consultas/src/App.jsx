import { AssistenteConsultas } from './components/AssistenteConsultas/AssistenteConsultas.jsx';

// "App já existente da Globalsys" simulado, só pra demonstrar o widget
// embutido — em produção o <AssistenteConsultas /> é importado dentro do
// app real, sem esse shell.
export function App() {
  return (
    <div style={{ minHeight: '100vh', background: '#FAF9F5' }}>
      <header
        style={{
          background:
            'linear-gradient(112.61deg, #041833 0%, #0000AA 24%, #1D1DDB 62%, #0F0FC3 81%, #00083D 100%)',
          height: 64,
          padding: '0 40px',
          display: 'flex',
          alignItems: 'center',
          color: '#FFFFFF',
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 600,
        }}
      >
        Globalsys — App
      </header>
      <main style={{ padding: 40 }}>
        <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#000A1E' }}>
          Dashboard (placeholder)
        </h1>
        <p style={{ color: 'rgba(0,10,30,0.65)', maxWidth: 480 }}>
          Conteúdo do app principal. O Assistente de Consultas fica ancorado
          no canto inferior direito, independente desta tela.
        </p>
      </main>
      <AssistenteConsultas />
    </div>
  );
}
