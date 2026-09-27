import { ConnectionProvider, WalletProvider, useWallet } from '@solana/wallet-adapter-react';
import { WalletModalProvider, WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { PhantomWalletAdapter } from '@solana/wallet-adapter-wallets';
import { clusterApiUrl } from '@solana/web3.js';
import { Activity, ScanSearch, ShieldCheck } from 'lucide-react';
import { Component, useCallback, useEffect, useMemo, useState } from 'react';
import PaymentCheckout from './components/PaymentCheckout';
import ReportViewer from './components/ReportViewer';
import StatusIndicator from './components/StatusIndicator';

import '@solana/wallet-adapter-react-ui/styles.css';

class PaymentCheckoutErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[Checkout] Erro de renderização capturado:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <section role="alert" className="rounded-2xl border border-red-400/30 bg-red-400/10 p-5 text-sm text-red-100">
          <p className="font-semibold">O checkout encontrou um erro inesperado.</p>
          <p className="mt-1 text-red-100/80">O restante do dashboard continua disponível. Tente carregar o checkout novamente.</p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false })}
            className="mt-3 rounded-lg border border-red-200/30 px-3 py-2 font-medium transition hover:bg-red-100/10"
          >
            Tentar novamente
          </button>
        </section>
      );
    }

    return this.props.children;
  }
}

function resolveApiBaseUrl() {
  const configuredUrl = import.meta.env.VITE_API_URL?.trim();
  const fallbackUrl = import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin;

  if (!configuredUrl) return fallbackUrl;

  try {
    const parsedUrl = new URL(configuredUrl);
    if (!['http:', 'https:'].includes(parsedUrl.protocol)) throw new Error('Protocolo inválido');
    if (!parsedUrl.port && ['localhost', '127.0.0.1'].includes(parsedUrl.hostname)) {
      parsedUrl.port = '8000';
    }
    return parsedUrl.toString().replace(/\/$/, '');
  } catch (error) {
    console.error('[Sentinela] VITE_API_URL inválida; usando fallback:', error);
    return fallbackUrl;
  }
}

function AppShell() {
  const [relatorio, setRelatorio] = useState(null);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);
  const [erroApi, setErroApi] = useState(false);
  const [scanNotice, setScanNotice] = useState('');
  const { connected, publicKey, signMessage } = useWallet();
  const [authToken, setAuthToken] = useState('');
  const [authWallet, setAuthWallet] = useState('');
  const [authenticating, setAuthenticating] = useState(false);
  const [authError, setAuthError] = useState('');

  const apiBaseUrl = resolveApiBaseUrl();
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

  const handleSiwsSignIn = useCallback(async () => {
    if (!connected || !publicKey) return;
    if (!signMessage) {
      setAuthError('Esta carteira não oferece suporte a assinatura de mensagens SIWS.');
      return;
    }

    setAuthenticating(true);
    setAuthError('');
    try {
      const address = publicKey.toBase58();
      const nonceResponse = await fetch(
        `${apiBaseUrl}/api/v1/auth/nonce?public_key=${encodeURIComponent(address)}`,
        { cache: 'no-store' },
      );
      const challenge = await nonceResponse.json();
      if (!nonceResponse.ok) throw new Error(challenge.detail || 'Não foi possível obter o nonce SIWS.');

      const signatureBytes = await signMessage(new TextEncoder().encode(challenge.message));
      const signature = Array.from(signatureBytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
      const verifyResponse = await fetch(`${apiBaseUrl}/api/v1/auth/verify-wallet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          public_key: address,
          signature,
          message: challenge.message,
          nonce: challenge.nonce,
        }),
      });
      const session = await verifyResponse.json();
      if (!verifyResponse.ok) throw new Error(session.detail || 'A assinatura SIWS não foi validada.');

      setAuthToken(session.access_token);
      setAuthWallet(address);
      setScanNotice('Carteira autenticada com SIWS.');
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'Falha ao autenticar a carteira.');
    } finally {
      setAuthenticating(false);
    }
  }, [apiBaseUrl, connected, publicKey, signMessage]);

  const handleVerifiedPayment = useCallback((payment) => {
    if (payment?.demo) {
      setScanNotice(`DEMO local: ${payment?.credits_added || 0} crédito(s) simulado(s); nenhum crédito real foi liberado.`);
      return;
    }
    setScanNotice(`Pagamento confirmado: ${payment?.credits_added || 0} crédito(s) liberado(s). Varredura iniciada.`);
  }, []);

  return (
    <div className="dashboard-shell min-h-screen px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
        <div className="absolute -left-40 -top-40 h-96 w-96 rounded-full bg-violet-600/10 blur-3xl" />
        <div className="absolute -right-40 top-1/3 h-96 w-96 rounded-full bg-emerald-400/10 blur-3xl" />
      </div>

      <header className="mx-auto mb-10 flex w-full max-w-7xl flex-col gap-6 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-emerald-300/20 bg-gradient-to-br from-emerald-300/15 to-violet-500/20 text-emerald-300 shadow-lg shadow-emerald-950/30">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300">Cyber intelligence</p>
            <h1 className="mt-1 text-2xl font-black tracking-tight text-white sm:text-3xl">Sentinela Digital</h1>
            <p className="mt-1 text-sm text-slate-400">Monitoramento de segurança em tempo real</p>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:items-end">
          <div className="flex flex-wrap items-center gap-2">
            <StatusIndicator lastUpdate={ultimaAtualizacao} online={!erroApi && Boolean(ultimaAtualizacao)} />
            <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium ${erroApi ? 'border-amber-400/20 bg-amber-400/10 text-amber-200' : 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200'}`}>
              <Activity className="h-3.5 w-3.5" />
              {erroApi ? 'API em modo fallback' : 'Backend conectado'}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {connected && publicKey ? (
              <span className="text-xs text-slate-400">
                {publicKey.toBase58().slice(0, 4)}…{publicKey.toBase58().slice(-4)}
              </span>
            ) : null}
            <WalletMultiButton className="!h-11 !rounded-xl !border !border-violet-300/20 !bg-violet-500/15 !px-4 !font-semibold !text-violet-100 transition hover:!bg-violet-500/25" />
            {connected ? (
              <button
                type="button"
                onClick={handleSiwsSignIn}
                disabled={authenticating || !signMessage}
                className="h-11 rounded-xl border border-emerald-300/20 bg-emerald-300/10 px-4 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {authenticating ? 'Aguardando assinatura…' : authToken && authWallet === publicKey?.toBase58() ? 'Carteira autenticada' : 'Autenticar SIWS'}
              </button>
            ) : null}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-8">
        <section className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-violet-300">Painel de operações</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">Centro de segurança</h2>
          </div>
          <p className="text-sm text-slate-400">
            {ultimaAtualizacao ? `Atualizado ${ultimaAtualizacao.toLocaleString('pt-BR')}` : 'Aguardando primeira sincronização'}
          </p>
        </section>

        {scanNotice ? (
          <div role="status" className="flex items-center gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
            <ShieldCheck className="h-5 w-5 shrink-0 text-emerald-300" />
            {scanNotice}
          </div>
        ) : null}
        {authError ? (
          <div role="alert" className="rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">
            {authError}
          </div>
        ) : null}

        <PaymentCheckoutErrorBoundary>
          <PaymentCheckout apiBaseUrl={apiBaseUrl} onVerified={handleVerifiedPayment} />
        </PaymentCheckoutErrorBoundary>

        <section aria-labelledby="report-heading">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-xl border border-cyan-300/20 bg-cyan-300/10 p-2 text-cyan-300">
              <ScanSearch className="h-5 w-5" />
            </div>
            <div>
              <h2 id="report-heading" className="text-lg font-semibold text-white">Resumo da auditoria</h2>
              <p className="text-sm text-slate-400">Achados e indicadores da última varredura</p>
            </div>
          </div>
          {relatorio ? (
            <ReportViewer key={relatorio.__key} data={relatorio} />
          ) : (
            <div className="rounded-2xl border border-dashed border-white/10 bg-slate-900/40 px-6 py-14 text-center">
              <ScanSearch className="mx-auto h-8 w-8 text-slate-600" />
              <p className="mt-4 font-medium text-slate-300">Aguardando dados da auditoria</p>
              <p className="mt-1 text-sm text-slate-500">Verifique se o backend está em execução para carregar o relatório.</p>
            </div>
          )}
        </section>
      </main>

      <footer className="mx-auto mt-12 w-full max-w-7xl border-t border-white/10 py-6 text-center text-xs text-slate-500">
        Sentinela Digital <span className="mx-2 text-slate-700">/</span> Plataforma de automação de segurança
      </footer>
    </div>
  );
}

function App() {
  const cluster = import.meta.env.VITE_SOLANA_CLUSTER || 'mainnet-beta';
  const endpoint = useMemo(() => clusterApiUrl(cluster), [cluster]);
  const wallets = useMemo(() => [new PhantomWalletAdapter()], []);

  return (
    <ConnectionProvider endpoint={endpoint}>
      <WalletProvider wallets={wallets} autoConnect>
        <WalletModalProvider>
          <AppShell />
        </WalletModalProvider>
      </WalletProvider>
    </ConnectionProvider>
  );
}

export default App;
