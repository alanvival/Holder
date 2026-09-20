import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // Porta fixa e explícita: o backend libera exatamente esta origem no
    // CORS (FRONTEND_ORIGIN em server.py). `strictPort` faz o Vite falhar
    // alto se a porta estiver ocupada, em vez de escolher outra em
    // silêncio — que é como a divergência 5173/5183 nasceu, e ela era
    // invisível: sem o cabeçalho de CORS o navegador descarta a resposta,
    // o chamarBackend devolve null e o assistente cai no modo local sem
    // reclamar de nada.
    port: 5173,
    strictPort: true,
  },
});
