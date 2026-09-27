import { useWallet } from '@solana/wallet-adapter-react';
import { Keypair } from '@solana/web3.js';
import { CheckCircle2, Copy, ExternalLink, Loader2, ScanLine, ShieldAlert } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 20;

const getWalletAddress = (publicKey) => {
  try {
    return typeof publicKey?.toBase58 === 'function' ? publicKey.toBase58() : '';
  } catch (err) {
    console.error('PaymentCheckout Error:', err);
    return '';
  }
};

const normalizePaymentData = (payload) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error('O backend retornou uma resposta de cobrança inválida.');
  }
  const paymentData = payload.paymentData && typeof payload.paymentData === 'object' ? payload.paymentData : {};
  const paymentUrl = payload.payment_url || payload.qr_payload || payload.solana_pay_url || paymentData.payment_url || paymentData.qr_payload;
  const qrCodeUrl = payload.qr_code_url || paymentData.qr_code_url;
  const reference = payload.reference || paymentData.reference;
  if ((!paymentUrl && !qrCodeUrl) || typeof reference !== 'string' || !reference.trim()) {
    throw new Error('A resposta do backend não contém o link de pagamento ou a referência da cobrança.');
  }
  return {
    ...payload,
    payment_url: typeof paymentUrl === 'string' ? paymentUrl : '',
    qr_code_url: typeof qrCodeUrl === 'string' ? qrCodeUrl : '',
    reference,
  };
};

const isPaymentConfirmed = (status) => ['verified', 'confirmed', 'paid'].includes(String(status || '').toLowerCase());

const PaymentCheckout = ({ apiBaseUrl, onVerified }) => {
  const { connected, publicKey } = useWallet();
  const walletAddress = getWalletAddress(publicKey);
  const solanaCluster = import.meta.env.VITE_SOLANA_CLUSTER || 'mainnet-beta';
  const [target, setTarget] = useState('');
  const [amountSol, setAmountSol] = useState('0.05');
  const [scansToCredit, setScansToCredit] = useState('1');
  const [note, setNote] = useState('Sentinela Digital pay-per-query');
  const [order, setOrder] = useState(null);
  const [paymentStatus, setPaymentStatus] = useState('idle');
  const [scanProgress, setScanProgress] = useState(0);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [txSignature, setTxSignature] = useState('');
  const stopPollingRef = useRef(false);
  const onVerifiedRef = useRef(onVerified);
  const isDemoEnabled = import.meta.env.DEV || import.meta.env.VITE_ENABLE_PAYMENT_DEMO === 'true';

  useEffect(() => {
    onVerifiedRef.current = onVerified;
  }, [onVerified]);

  const paymentUrl = typeof order?.payment_url === 'string' ? order.payment_url : '';

  const qrUrl = useMemo(() => {
    if (!paymentUrl) return '';
    return `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(paymentUrl)}`;
  }, [paymentUrl]);
  const qrImageUrl = typeof order?.qr_code_url === 'string' && order.qr_code_url ? order.qr_code_url : qrUrl;

  useEffect(() => {
    try {
      if (!['verified', 'SCAN_IN_PROGRESS'].includes(paymentStatus)) return undefined;
      const interval = window.setInterval(() => {
        try {
          setScanProgress((current) => Math.min(current + 15, 100));
        } catch (err) {
          console.error('PaymentCheckout Error:', err);
          window.clearInterval(interval);
        }
      }, 500);
      return () => window.clearInterval(interval);
    } catch (err) {
      console.error('PaymentCheckout Error:', err);
      return undefined;
    }
  }, [paymentStatus]);

  useEffect(() => {
    try {
      if (typeof order?.reference !== 'string' || !order.reference || stopPollingRef.current) return undefined;
      let cancelled = false;
      let timerId;
      let attempts = 0;
      let pollInFlight = false;
      const poll = async () => {
        if (cancelled || stopPollingRef.current || pollInFlight) return;
        if (attempts >= MAX_POLL_ATTEMPTS) {
          stopPollingRef.current = true;
          setError('A verificação atingiu o limite de tentativas. Use “Verificar assinatura” ou gere uma nova cobrança.');
          setPaymentStatus('error');
          return;
        }
        attempts += 1;
        pollInFlight = true;
        try {
          const response = await fetch(`${apiBaseUrl}/api/v1/payments/verify-tx`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              reference: order.reference,
              wallet_address: getWalletAddress(publicKey) || order?.wallet_address || undefined,
              scans_to_credit: Number(order?.scans_to_credit) || 1,
              expected_amount_sol: Number(order?.amount_sol) || undefined,
              ...(txSignature?.trim() ? { txSignature: txSignature.trim() } : {}),
            }),
          });

          const data = await response.json().catch((err) => {
            console.error('PaymentCheckout Error:', err);
            return {};
          });
          if (!response.ok) {
            const detail = data?.detail || `HTTP ${response.status}`;
            console.error('[Solana Pay] Falha na verificação do pagamento:', detail);
            setError(`Não foi possível verificar o pagamento (${detail}). Verifique conexão, CORS e o backend.`);
            if (response.status >= 400 && response.status < 500 && ![408, 429].includes(response.status)) {
              stopPollingRef.current = true;
              setPaymentStatus('error');
              return;
            }
            setPaymentStatus('pending');
            return;
          }

          if (data?.status === 'error' && /reference inválida|publickey/i.test(String(data?.message || ''))) {
            stopPollingRef.current = true;
            setError(data.message);
            setPaymentStatus('error');
            return;
          }

          setError('');
          if (isPaymentConfirmed(data?.status) || Number(data?.credits_added) > 0 || data?.confirmed === true || data?.paid === true) {
            stopPollingRef.current = true;
            setPaymentStatus('SCAN_IN_PROGRESS');
            setScanProgress(35);
            onVerifiedRef.current?.({ ...data, status: 'SCAN_IN_PROGRESS' });
            return;
          }

          setPaymentStatus(typeof data?.status === 'string' ? data.status : 'pending');
        } catch (pollError) {
          console.error('PaymentCheckout Error:', pollError);
          const message = pollError instanceof Error ? pollError.message : 'Erro inesperado ao verificar pagamento';
          console.error('[Solana Pay] Erro de rede/CORS durante polling; uma nova tentativa ocorrerá em 3 s:', pollError);
          setError(`Falha de conexão ao verificar pagamento: ${message}. Confira CORS e disponibilidade da API.`);
          setPaymentStatus('pending');
        } finally {
          pollInFlight = false;
          if (!cancelled && !stopPollingRef.current && attempts >= MAX_POLL_ATTEMPTS) {
            stopPollingRef.current = true;
            setError('A verificação atingiu o limite de tentativas. Use “Verificar assinatura” ou gere uma nova cobrança.');
            setPaymentStatus('error');
          } else if (!cancelled && !stopPollingRef.current) {
            timerId = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
          }
        }
      };

      void poll();
      return () => {
        cancelled = true;
        if (timerId !== undefined) window.clearTimeout(timerId);
      };
    } catch (err) {
      console.error('PaymentCheckout Error:', err);
      return undefined;
    }
  }, [apiBaseUrl, order?.reference, order?.wallet_address, order?.scans_to_credit, order?.amount_sol, publicKey, txSignature]);

  const handleCreateOrder = async () => {
    let controller;
    let timeoutId;
    try {
      setError('');
      setPaymentStatus('idle');

      const walletAddress = getWalletAddress(publicKey);
      if (!connected || !walletAddress) {
        setError('Conecte uma carteira Solana válida para gerar a cobrança.');
        return;
      }
      if (isLoading) return;

      console.log('Iniciando geração de cobrança...', target);
      setIsLoading(true);
      stopPollingRef.current = false;
      const referenceBase58 = Keypair.generate().publicKey.toBase58();
      controller = new AbortController();
      timeoutId = window.setTimeout(() => controller.abort(), 15000);
      const response = await fetch(`${apiBaseUrl}/api/v1/payments/create-order`, {
        method: 'POST',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: publicKey.toBase58(),
          reference: referenceBase58,
          amount_sol: Number(amountSol),
          scans_to_credit: Number(scansToCredit) || 1,
          target: target || null,
          note,
        }),
      });
      console.log('Resposta do backend:', response);

      const payload = await response.json().catch((err) => {
        console.error('PaymentCheckout Error:', err);
        throw new Error('O backend retornou um JSON inválido ao criar a cobrança.');
      });
      if (!response.ok) {
        throw new Error(payload?.detail || `O backend recusou a solicitação (HTTP ${response.status}).`);
      }

      const paymentData = normalizePaymentData(payload);
      if (paymentData.reference !== referenceBase58) {
        throw new Error('O backend retornou uma referência diferente da referência Base58 solicitada.');
      }
      setOrder({
        ...paymentData,
        wallet_address: walletAddress,
        amount_sol: Number(amountSol),
        scans_to_credit: Number(scansToCredit) || 1,
      });
      setPaymentStatus('pending');
      setScanProgress(10);
      setTxSignature('');
      console.info('[Solana Pay] Cobrança criada. QR/link exibido; polling iniciado.', {
        reference: paymentData.reference,
      });
    } catch (createError) {
      console.error('PaymentCheckout Error:', createError);
      if (typeof DOMException !== 'undefined' && createError instanceof DOMException && createError.name === 'AbortError') {
        setError(`O backend não respondeu em 15 segundos. Confira se a API está ativa em ${apiBaseUrl} e se CORS permite esta origem.`);
      } else if (createError instanceof TypeError) {
        setError(`Não foi possível conectar ao backend em ${apiBaseUrl}. Confira se o FastAPI está rodando na porta 8000, a URL VITE_API_URL e a configuração de CORS.`);
      } else {
        setError(createError instanceof Error ? createError.message : 'Falha inesperada ao criar a cobrança. Tente novamente.');
      }
    } finally {
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      setIsLoading(false);
    }
  };

  const copyPaymentUrl = async () => {
    try {
      if (typeof paymentUrl !== 'string' || !paymentUrl) throw new Error('Link de pagamento indisponível.');
      await navigator.clipboard.writeText(paymentUrl);
    } catch (err) {
      console.error('PaymentCheckout Error:', err);
      setError('Não foi possível copiar o link de pagamento.');
    }
  };

  const handleVerifyTransactionSignature = async () => {
    try {
      if (typeof order?.reference !== 'string' || !order.reference || !txSignature?.trim()) return;
      setError('');
      const response = await fetch(`${apiBaseUrl}/api/v1/payments/verify-tx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reference: order.reference,
          txSignature: txSignature.trim(),
          wallet_address: getWalletAddress(publicKey) || order?.wallet_address,
        }),
      });
      const data = await response.json().catch((err) => {
        console.error('PaymentCheckout Error:', err);
        return {};
      });
      if (!response.ok) throw new Error(data?.detail || `HTTP ${response.status}`);
      if (isPaymentConfirmed(data?.status) || Number(data?.credits_added) > 0 || data?.confirmed === true || data?.paid === true) {
        stopPollingRef.current = true;
        setPaymentStatus('SCAN_IN_PROGRESS');
        setScanProgress(35);
        setError('');
        onVerifiedRef.current?.({ ...data, status: 'SCAN_IN_PROGRESS' });
      } else {
        setPaymentStatus(typeof data?.status === 'string' ? data.status : 'pending');
        setError(data?.message || 'A transação ainda não pôde ser confirmada.');
      }
    } catch (verifyError) {
      console.error('PaymentCheckout Error:', verifyError);
      const message = verifyError instanceof Error ? verifyError.message : 'Erro inesperado';
      if (/reference inválida|publickey|HTTP 4\d\d/i.test(message)) {
        stopPollingRef.current = true;
        setPaymentStatus('error');
      }
      console.error('[Solana Pay] Falha ao verificar assinatura informada:', verifyError);
      setError(`Falha ao verificar a assinatura: ${message}`);
    }
  };

  const handleDemoConfirmation = () => {
    try {
      stopPollingRef.current = true;
      const simulatedPayment = {
        status: 'verified',
        credits_added: Number(order?.scans_to_credit) || 1,
        demo: true,
      };
      setPaymentStatus('verified');
      setScanProgress(100);
      setError('');
      onVerified?.(simulatedPayment);
    } catch (err) {
      console.error('PaymentCheckout Error:', err);
      setError('Não foi possível simular a confirmação da demonstração.');
    }
  };

  return (
    <section translate="no" className="overflow-hidden rounded-3xl border border-violet-300/15 bg-gradient-to-br from-slate-900 via-slate-950 to-[#101329] p-5 text-slate-100 shadow-2xl shadow-black/30 sm:p-7">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-violet-300/20 bg-violet-400/10 p-3 text-violet-200 shadow-lg shadow-violet-950/30">
            <ScanLine className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-300">Micropagamentos</p>
            <h2 className="mt-1 text-xl font-bold text-white">Checkout Solana Pay</h2>
            <p className="mt-1 text-sm text-slate-400">Libere créditos de varredura com confirmação on-chain.</p>
          </div>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-2 text-xs font-semibold text-emerald-200">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_10px_#6ee7b7]" /> Solana {solanaCluster === 'devnet' ? 'Devnet' : 'Mainnet'}
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Alvo da auditoria</span>
          <input
            value={target}
            onChange={(event) => setTarget(event.target.value)}
            placeholder="Carteira Solana, domínio .sol, e-mail ou URL"
            maxLength={255}
            className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
          />
        </label>
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Valor (SOL)</span>
          <input
            value={amountSol}
            onChange={(event) => setAmountSol(event.target.value)}
            inputMode="decimal"
            className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
          />
        </label>
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Créditos de scan</span>
          <input
            value={scansToCredit}
            onChange={(event) => setScansToCredit(event.target.value)}
            inputMode="numeric"
            className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
          />
        </label>
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Nota da cobrança</span>
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-300/10"
          />
        </label>
      </div>

      <div className="mt-5 flex flex-col gap-4 border-t border-white/10 pt-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-xs text-slate-400">
          {connected && walletAddress ? `Carteira ativa: ${walletAddress.slice(0, 4)}…${walletAddress.slice(-4)}` : 'Conecte sua carteira Phantom para continuar.'}
        </div>
        <button
          type="button"
          onClick={handleCreateOrder}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-violet-950/40 transition hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-violet-300/60 disabled:cursor-wait disabled:opacity-60"
        >
          <span key="checkout-spinner-container" translate="no" className="relative inline-flex h-4 w-4 shrink-0 items-center justify-center">
            <Loader2 aria-hidden="true" className={`absolute h-4 w-4 ${isLoading ? 'animate-spin opacity-100' : 'opacity-0'}`} />
            <ShieldAlert aria-hidden="true" className={`absolute h-4 w-4 ${isLoading ? 'opacity-0' : 'opacity-100'}`} />
          </span>
          <span translate="no">{isLoading ? 'Gerando cobrança…' : 'Gerar cobrança'}</span>
        </button>
      </div>

      {error ? (
        <div role="alert" className="mt-4 rounded-xl border border-red-400/20 bg-red-400/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      {order ? (
        <div className="mt-6 grid gap-5 rounded-2xl border border-white/10 bg-black/20 p-4 sm:p-5 lg:grid-cols-[240px_1fr]">
          <div className="flex flex-col items-center justify-center rounded-xl border border-white/10 bg-slate-950/70 p-4">
            {qrImageUrl ? (
              <img src={qrImageUrl} alt="QR Code Solana Pay" className="h-[200px] w-[200px] rounded-xl bg-white p-2 sm:h-[220px] sm:w-[220px]" />
            ) : (
              <div className="flex h-[200px] w-[200px] items-center justify-center rounded-xl border border-dashed border-white/15 p-4 text-center text-xs text-slate-400 sm:h-[220px] sm:w-[220px]">
                QR Code indisponível. Use o link Solana Pay abaixo.
              </div>
            )}
            <p className="mt-3 text-xs text-slate-400">Escaneie com sua carteira Solana</p>
          </div>
          <div className="space-y-4">
            <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Status da transação</p>
                  <p className={`mt-1 font-semibold ${paymentStatus === 'verified' ? 'text-emerald-300' : 'text-violet-200'}`}>
                    {paymentStatus === 'verified' ? 'Pagamento confirmado' : paymentStatus === 'SCAN_IN_PROGRESS' ? 'Pagamento confirmado · varredura em andamento…' : paymentStatus === 'pending' ? 'Aguardando confirmação on-chain…' : paymentStatus}
                  </p>
                </div>
                {paymentStatus === 'verified' ? <CheckCircle2 className="h-5 w-5 text-emerald-300" /> : <Loader2 className="h-5 w-5 animate-spin text-violet-300" />}
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10" role="progressbar" aria-valuenow={scanProgress} aria-valuemin="0" aria-valuemax="100">
                <div className="h-full rounded-full bg-gradient-to-r from-violet-400 to-emerald-300 transition-all" style={{ width: `${scanProgress}%` }} />
              </div>
              <p className="mt-2 text-right text-xs text-slate-500">Verificação a cada 3 s, até 20 tentativas</p>
            </div>

            <div className="space-y-2 rounded-xl border border-white/10 bg-slate-950/60 p-4 text-sm">
              <p className="break-all text-slate-300"><span className="text-slate-500">Referência: </span><span className="font-mono text-xs">{order?.reference || 'n/d'}</span></p>
              <p className="break-all text-slate-300"><span className="text-slate-500">Pagamento: </span><span className="font-mono text-xs">{paymentUrl || order?.qr_code_url || 'Link indisponível'}</span></p>
              <p className="text-slate-300"><span className="text-slate-500">Créditos: </span>{order?.scans_to_credit ?? scansToCredit ?? '1'}</p>
            </div>

            <div className="space-y-3 rounded-xl border border-white/10 bg-slate-950/40 p-4">
              <label className="block space-y-2">
                <span htmlFor="payment-transaction-signature" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Assinatura da transação (opcional)</span>
                <input
                  id="payment-transaction-signature"
                  value={txSignature}
                  onChange={(event) => setTxSignature(event.target.value)}
                  placeholder="Cole a assinatura da transação Solana"
                  className="w-full rounded-lg border border-white/10 bg-slate-950 px-3 py-2 font-mono text-xs text-white outline-none placeholder:text-slate-600 focus:border-cyan-300/50"
                />
              </label>
              <button
                type="button"
                onClick={handleVerifyTransactionSignature}
                disabled={!txSignature.trim() || paymentStatus === 'verified'}
                className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-300/15 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Verificar assinatura no RPC
              </button>
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="button" onClick={copyPaymentUrl} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-violet-300/30 hover:bg-white/5">
                <Copy className="h-4 w-4" /> Copiar link Solana Pay
              </button>
              <a href={paymentUrl} className="inline-flex items-center gap-2 rounded-xl bg-emerald-300 px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-emerald-200">
                <ExternalLink className="h-4 w-4" /> Abrir na carteira
              </a>
            </div>
            {isDemoEnabled && paymentStatus !== 'verified' ? (
              <div className="rounded-xl border border-amber-300/20 bg-amber-300/[0.06] p-4">
                <p className="mb-3 text-xs leading-relaxed text-amber-100/80">
                  Simula somente o estado visual para apresentação. Não confirma uma transação nem credita a conta no backend.
                </p>
                <button
                  type="button"
                  onClick={handleDemoConfirmation}
                  className="inline-flex items-center gap-2 rounded-xl border border-amber-300/30 bg-amber-300/10 px-4 py-2.5 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/15"
                >
                  <ShieldAlert className="h-4 w-4" /> [Dev/Demo] Simular confirmação
                </button>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
};

export default PaymentCheckout;
