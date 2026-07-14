import { useEffect, useState } from 'react';
import ReportViewer from './components/ReportViewer';
import StatusIndicator from './components/StatusIndicator';

function App() {
  const [relatorio, setRelatorio] = useState(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    const carregarDados = async () => {
      try {
        // Aponte para a URL correta do seu backend no Render
        const API_URL = 'https://sentinela-digital-cxk8.onrender.com/relatorios/ultimo';
        
        const resposta = await fetch(API_URL);
        
        if (!resposta.ok) {
          throw new Error('Falha na resposta do servidor');
        }

        const dados = await resposta.json();
        
        // Verifica se os dados não estão vazios antes de atualizar
        if (dados && Object.keys(dados).length > 0) {
          setRelatorio(prev => {
            if (JSON.stringify(prev) !== JSON.stringify(dados)) {
              return dados;
            }
            return prev;
          });
          setUltimaAtualizacao(new Date());
          setErro(false);
        }
      } catch (err) {
        console.error("Erro ao carregar relatório do backend:", err);
        setErro(true);
      }
    };

    // Primeira chamada imediata
    carregarDados();
    
    // Intervalo de 5 segundos para atualizar a tela
    const intervalo = setInterval(carregarDados, 5000);
    
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
          <ReportViewer 
            key={`${relatorio.alvo}-${relatorio.gerado_em}`} 
            data={relatorio} 
          />
        ) : (
          <div className="text-center text-gray-500">
            {erro ? (
              <p className="text-red-500">Erro ao conectar com o servidor. Verifique o console.</p>
            ) : (
              <p>Aguardando dados do servidor...</p>
            )}
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