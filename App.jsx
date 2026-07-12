import { useEffect, useState } from 'react';
import ReportViewer from './components/ReportViewer';
import StatusIndicator from './components/StatusIndicator';

function App() {
  const [relatorio, setRelatorio] = useState(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);

  useEffect(() => {
    const carregarDados = async () => {
      try {
        // A constante cacheBuster garante que o navegador entenda a requisição como nova
        const cacheBuster = `?t=${new Date().getTime()}`;
        const resposta = await fetch(`/relatorios/ultimo_relatorio.json${cacheBuster}`, {
          cache: 'no-store'
        });

        if (resposta.ok) {
          const dados = await resposta.json();
          setRelatorio(dados);
          setUltimaAtualizacao(new Date());
        }
      } catch (err) {
        console.error("Erro ao carregar relatório:", err);
      }
    };

    // Carrega na montagem
    carregarDados();

    // Configura intervalo de 3 segundos
    const intervalo = setInterval(carregarDados, 3000);

    return () => clearInterval(intervalo);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 py-10 px-4">
      <header className="max-w-4xl mx-auto mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Sentinela Digital</h1>
          <p className="text-gray-600">Monitoramento em tempo real.</p>
          {relatorio && (
            <p className="text-sm text-gray-500 mt-2 font-semibold">
              Alvo atual: {relatorio.alvo}
            </p>
          )}
        </div>
        <StatusIndicator lastUpdate={ultimaAtualizacao} />
      </header>

      <main>
        {relatorio ? (
          <ReportViewer data={relatorio} />
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-500 animate-pulse">Aguardando dados...</p>
          </div>
        )}
      </main>

      <footer className="max-w-4xl mx-auto mt-10 text-center text-sm text-gray-400">
        Gerado pelo sistema de automação de segurança.
      </footer>
    </div>
  );
}

export default App;
