import { useEffect, useState } from 'react';
import ReportViewer from './components/ReportViewer';
import StatusIndicator from './components/StatusIndicator';

function App() {
  const [relatorio, setRelatorio] = useState(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);
  const [erroApi, setErroApi] = useState(false);

  const apiBaseUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  const endpointUrl = `${apiBaseUrl}/relatorios/ultimo`;

  useEffect(() => {
    let isMounted = true;

    const carregarDados = async () => {
      try {
        // Tenta buscar da API
        const resposta = await fetch(endpointUrl, { cache: 'no-store' });
        
        if (!resposta.ok) throw new Error('API indisponível');
        
        const dados = await resposta.json();
        if (!isMounted) return;

        processarDados(dados);
        setErroApi(false);
      } catch (err) {
        console.warn('API falhou, tentando fallback local...', err);
        setErroApi(true);
        
        // Fallback: Tenta ler o arquivo estático diretamente
        try {
          const resLocal = await fetch('/relatorios/ultimo_relatorio.json', { cache: 'no-store' });
          if (resLocal.ok) {
            const dadosLocais = await resLocal.json();
            if (isMounted) processarDados(dadosLocais);
          }
        } catch (e) {
          console.error('Falha crítica ao carregar dados locais:', e);
        }
      }
    };

    const processarDados = (dados) => {
      setRelatorio(prev => {
        const novaChave = `${dados?.alvo || 'sem-alvo'}-${dados?.gerado_em || 'sem-data'}`;
        const antigaChave = `${prev?.alvo || 'sem-alvo'}-${prev?.gerado_em || 'sem-data'}`;
        return novaChave !== antigaChave ? { ...dados, __key: novaChave } : prev;
      });
      setUltimaAtualizacao(new Date());
    };

    carregarDados();
    const intervalo = window.setInterval(carregarDados, 5000);
    const onFocus = () => carregarDados();

    window.addEventListener('focus', onFocus);
    window.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') carregarDados();
    });

    return () => {
      isMounted = false;
      window.clearInterval(intervalo);
      window.removeEventListener('focus', onFocus);
    };
  }, [endpointUrl]);

  return (
    <div className="min-h-screen bg-gray-100 py-10 px-4">
      <header className="max-w-4xl mx-auto mb-8 flex justify-between items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-gray-900">Sentinela Digital</h1>
          <p className="text-gray-600">Monitoramento em tempo real.</p>
          <p className="text-sm text-gray-500 mt-1">
            {relatorio?.alvo ? `Alvo atual: ${relatorio.alvo}` : 'Aguardando alvo do último scan...'}
          </p>
          <p className="text-sm font-medium mt-1">
            {erroApi ? (
              <span className="text-amber-600">⚠ Modo Offline (Lendo cache local)</span>
            ) : (
              <span className="text-green-600">● Conectado ao Backend</span>
            )}
          </p>
          <p className="text-sm text-gray-500">
            {ultimaAtualizacao ? `Última atualização: ${ultimaAtualizacao.toLocaleString('pt-BR')}` : 'Ainda não houve atualização'}
          </p>
        </div>
        <StatusIndicator lastUpdate={ultimaAtualizacao} />
      </header>

      <main>
        {relatorio ? (
          <ReportViewer key={relatorio.__key} data={relatorio} />
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-500">Aguardando dados... Verifique se o backend está rodando.</p>
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
