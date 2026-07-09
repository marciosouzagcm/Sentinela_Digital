import { useEffect, useState } from 'react';
import ReportViewer from './components/ReportViewer';
import StatusIndicator from './components/StatusIndicator';

function App() {
  const [relatorio, setRelatorio] = useState(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);

  useEffect(() => {
    const carregarDados = async () => {
      try {
        const resposta = await fetch('/relatorios/ultimo_relatorio.json');
        if (resposta.ok) {
          const dados = await resposta.json();
          setRelatorio(dados);
          setUltimaAtualizacao(new Date());
        }
      } catch (err) {
        console.error("Erro ao carregar relatório:", err);
      }
    };

    carregarDados();
    const intervalo = setInterval(carregarDados, 3000);
    return () => clearInterval(intervalo);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 py-10 px-4">
      <header className="max-w-4xl mx-auto mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Sentinela Digital</h1>
          <p className="text-gray-600">Monitoramento em tempo real.</p>
        </div>
        <StatusIndicator lastUpdate={ultimaAtualizacao} />
      </header>

      <main>
        {relatorio ? (
          <ReportViewer data={relatorio} />
        ) : (
          <p className="text-center text-gray-500">Aguardando dados...</p>
        )}
      </main>

      <footer className="max-w-4xl mx-auto mt-10 text-center text-sm text-gray-400">
        Gerado pelo sistema de automação de segurança.
      </footer>
    </div>
  );
}

export default App;
