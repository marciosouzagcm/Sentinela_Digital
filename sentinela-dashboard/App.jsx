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
        
        // URL absoluta para a sua API FastAPI no Render
        // Inclui o 't' para evitar cache do navegador
        const API_URL = `https://sentinela-digital-cxk8.onrender.com/relatorios/ultimo?t=${Date.now()}`;
        
        const resposta = await fetch(API_URL, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          }
        });
        
        if (!resposta.ok) {
          throw new Error(`Erro HTTP: ${resposta.status}`);
        }
        
        const dados = await resposta.json();
        
        // Validação básica: verifica se o objeto não está vazio
        if (dados && Object.keys(dados).length > 0) {
          setRelatorio(dados);
          setUltimaAtualizacao(new Date());
          setDebug("Dados carregados com sucesso.");
        } else {
          setDebug("Nenhum relatório disponível no momento.");
        }
      } catch (err) {
        console.error("Erro na busca da API:", err);
        setDebug(`Erro na API: ${err.message}`);
      }
    };

    // Executa a primeira vez
    carregarDados();
    
    // Configura o intervalo de atualização para 10 segundos
    const intervalo = setInterval(carregarDados, 10000);
    
    // Limpa o intervalo ao desmontar o componente
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
              Se o status mostrar erro, verifique o console do navegador (F12).
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;