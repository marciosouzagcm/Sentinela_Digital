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
        // URL corrigida para o caminho exato do arquivo estático no Render
        const API_URL = `https://sentinela-digital-cxk8.onrender.com/relatorios/ultimo?t=${Date.now()}`
        
        const resposta = await fetch(API_URL);
        
        if (!resposta.ok) {
          throw new Error(`HTTP ${resposta.status}`);
        }
        
        const dados = await resposta.json();
        
        // Verifica se o objeto recebido possui a estrutura mínima esperada
        if (dados && (dados.alvo || dados.categorias)) {
          setRelatorio(dados);
          setUltimaAtualizacao(new Date());
          setDebug("Dados carregados com sucesso.");
        } else {
          setDebug("Dados recebidos, mas o formato é inválido.");
        }
      } catch (err) {
        console.error("Erro na busca da API:", err);
        setDebug(`Erro na API: ${err.message}`);
      }
    };

    // Execução inicial
    carregarDados();
    
    // Atualização automática a cada 10 segundos
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
        {relatorio ? (
          <ReportViewer data={relatorio} />
        ) : (
          <div className="bg-white p-10 rounded-lg shadow-sm text-center border border-gray-200">
            <p className="text-gray-500">Aguardando dados do monitoramento...</p>
            <p className="text-xs text-gray-400 mt-2">
              Se o status mostrar erro, verifique as permissões de CORS no Render.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;