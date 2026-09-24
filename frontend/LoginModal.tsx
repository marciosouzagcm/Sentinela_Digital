import { useState } from 'react';

export default function LoginModal() {
  const [method, setMethod] = useState<'wallet' | 'email'>('wallet');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-6">
      <div className="w-full max-w-xl rounded-3xl border border-slate-800 bg-[#0b1226] p-6 shadow-2xl shadow-[#9945FF]/15">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-[#14F195]">Autenticação</div>
            <h3 className="mt-2 text-2xl font-black text-white">Conectar conta</h3>
          </div>
          <button className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-300">Fechar</button>
        </div>

        <div className="mt-6 flex gap-2 rounded-full border border-slate-800 bg-slate-900 p-1">
          {['wallet', 'email'].map((option) => (
            <button
              key={option}
              onClick={() => setMethod(option as 'wallet' | 'email')}
              className={`flex-1 rounded-full px-3 py-2 text-sm font-semibold ${method === option ? 'bg-gradient-to-r from-[#9945FF] to-[#14F195] text-slate-950' : 'text-slate-300'}`}
            >
              {option === 'wallet' ? 'Wallet SIWS' : 'E-mail / senha'}
            </button>
          ))}
        </div>

        {method === 'wallet' ? (
          <div className="mt-6 space-y-4">
            <div className="rounded-2xl border border-[#14F195]/30 bg-[#14F195]/5 p-4 text-sm text-slate-200">
              Assine a mensagem SIWS para autenticar a carteira Phantom ou Solflare. A assinatura é validada no backend contra nonce temporário.
            </div>
            <button className="w-full rounded-full bg-gradient-to-r from-[#9945FF] to-[#14F195] px-4 py-3 font-bold text-slate-950">
              Conectar Phantom / Solflare
            </button>
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            <input className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none" placeholder="seu@email.com" />
            <input type="password" className="w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none" placeholder="senha" />
            <button className="w-full rounded-full border border-slate-700 bg-slate-900 px-4 py-3 font-bold text-white">
              Entrar com e-mail
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
