import { useEffect, useState } from 'react';
import ReportViewer from './components/ReportViewer';
import StatusIndicator from './components/StatusIndicator';

function App() {
  const [relatorio, setRelatorio] = useState(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);
  const [debug, setDebug] = useState("Iniciando...");

  useEffect(() => {
    const carregarDados = async () => {
      try {
        setDebug("Buscando dados no servidor...");
        // URL absoluta e corrigida para a API FastAPI no Render
        const API_URL = `https://sentinela-digital-cxk8.onrender.com/relatorios/ultimo?t=${Date.now()}`;
        
        const resposta = await fetch(API_URL);
        
        if (!resposta.ok) {
          throw new Error(`HTTP ${resposta.status}`);
        }
        
        const dados = await resposta.json();
        setRelatorio(dados);
        setUltimaAtualizacao(new Date());
        setDebug("Dados carregados com sucesso.");
      } catch (err) {
        setDebug(`Erro na API: ${err.message}`);
      }
    };

    carregarDados();
    const intervalo = setInterval(carregarDados, 10000);
    return () => clearInterval(intervalo);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 py-10 px-4">
      <header className="max-w-4xl mx-auto mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Sentinela Digital</h1>
          <p className="text-sm text-gray-500 font-medium mt-1">Status: {debug}</p>
        </div>
        <StatusIndicator lastUpdate={ultimaAtualizacao} />
      </header>
      <main className="max-w-4xl mx-auto">
        {relatorio ? <ReportViewer data={relatorio} /> : <p className="text-center">Carregando...</p>}
      </main>
    </div>
  );
}

export default App;