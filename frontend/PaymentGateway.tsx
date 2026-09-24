import { useState } from 'react';

export default function PaymentGateway() {
  const [currency, setCurrency] = useState<'SOL' | 'USDC'>('USDC');
  const [amount, setAmount] = useState('49');

  return (
    <div className="rounded-3xl border border-slate-800 bg-[#0b1226] p-6 shadow-xl shadow-[#14F195]/10">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.3em] text-[#14F195]">Pagamentos Solana</div>
          <h3 className="mt-2 text-2xl font-black text-white">Checkout de créditos</h3>
        </div>
        <div className="rounded-full border border-[#14F195]/30 bg-[#14F195]/10 px-3 py-2 text-xs uppercase tracking-[0.2em] text-[#14F195]">
          On-chain
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <button
          onClick={() => setCurrency('USDC')}
          className={`rounded-2xl border px-4 py-3 font-bold ${currency === 'USDC' ? 'border-[#14F195] bg-[#14F195]/10 text-[#14F195]' : 'border-slate-700 text-slate-300'}`}
        >
          USDC SPL-Token
        </button>
        <button
          onClick={() => setCurrency('SOL')}
          className={`rounded-2xl border px-4 py-3 font-bold ${currency === 'SOL' ? 'border-[#9945FF] bg-[#9945FF]/10 text-[#9945FF]' : 'border-slate-700 text-slate-300'}`}
        >
          SOL nativo
        </button>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950 p-4">
        <div className="text-xs uppercase tracking-[0.22em] text-slate-400">Qtd. de créditos</div>
        <div className="mt-4 flex items-center justify-between gap-4">
          <label className="text-sm text-slate-300">Valor do pagamento</label>
          <input value={amount} onChange={(event) => setAmount(event.target.value)} className="w-24 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-right text-white" />
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-dashed border-[#9945FF]/40 bg-[#9945FF]/5 p-4 text-sm text-slate-200">
        <div className="font-semibold text-white">Carteira da tesouraria</div>
        <div className="mt-2 break-all">5tG4...S1eQ6Xn5dHnpKq3cA5CkM7jPZ6E9V</div>
      </div>

      <div className="mt-8 flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950 p-4">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Total</div>
          <div className="mt-1 text-2xl font-black text-white">{currency} {amount}</div>
        </div>
        <button className="rounded-full bg-gradient-to-r from-[#9945FF] to-[#14F195] px-5 py-3 font-bold text-slate-950">
          Confirmar transação
        </button>
      </div>
    </div>
  );
}
