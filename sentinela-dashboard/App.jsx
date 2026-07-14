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
        setDebug("Buscando dados...");
        const API_URL = 'https://sentinela-digital-cxk8.onrender.com/relatorios/ultimo';
        const resposta = await fetch(API_URL);
        
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        
        const dados = await resposta.json();
        
        if (dados && dados.alvo) {
          setRelatorio(dados);
          setUltimaAtualizacao(new Date());
          setDebug("Dados carregados com sucesso.");
        } else {
          setDebug("JSON vazio ou formato inesperado.");
        }
      } catch (err) {
        console.error("Erro:", err);
        setDebug(`Erro na API: ${err.message}`);
      }
    };

    carregarDados();
    const intervalo = setInterval(carregarDados, 10000); // Aumentado para 10s
    return () => clearInterval(intervalo);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 py-10 px-4">
      <header className="max-w-4xl mx-auto mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Sentinela Digital</h1>
          <p className="text-gray-600">Status: {debug}</p>
        </div>
        <StatusIndicator lastUpdate={ultimaAtualizacao} />
      </header>

      <main>
        {relatorio ? (
          <ReportViewer data={relatorio} />
        ) : (
          <div className="text-center text-gray-500">
            <p>Carregando dados do monitoramento...</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;