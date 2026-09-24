
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#050816] text-white">
      <header className="mx-auto max-w-7xl px-6 py-8">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] font-black text-[#050816]">
              S
            </div>
            <div>
              <div className="text-lg font-black tracking-wide">Sentinela Digital</div>
              <div className="text-[10px] uppercase tracking-[0.3em] text-slate-400">CyberIntel OSINT</div>
            </div>
          </div>
          <div className="hidden gap-8 text-sm text-slate-300 md:flex">
            <a href="#product">Produto</a>
            <a href="#pricing">Preços</a>
            <a href="#security">Segurança</a>
            <a href="#legal">Legal</a>
          </div>
          <button className="rounded-full border border-[#14F195]/40 bg-[#14F195]/10 px-4 py-2 text-sm font-semibold text-[#14F195]">
            Conectar carteira
          </button>
        </nav>
      </header>

      <main className="mx-auto max-w-7xl px-6 pb-20">
        <section className="grid items-center gap-10 py-12 lg:grid-cols-2">
          <div>
            <div className="mb-6 inline-flex rounded-full border border-[#9945FF]/50 bg-[#9945FF]/10 px-3 py-1 text-xs uppercase tracking-[0.28em] text-[#c8a4ff]">
              Threat Intelligence as a Service
            </div>
            <h1 className="max-w-xl text-5xl font-black leading-tight tracking-tight md:text-6xl">
              CyberIntel para <span className="text-[#14F195]">web3</span>, risco e reputação digital.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-slate-300">
              Audite e-mails, carteiras e exposições digitais com relatórios executivos, score de risco e provas em PDF para decisões ágeis.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <button className="rounded-full bg-gradient-to-r from-[#9945FF] to-[#14F195] px-6 py-3 font-bold text-slate-950 shadow-lg shadow-[#14F195]/20">
                Iniciar varredura
              </button>
              <button className="rounded-full border border-slate-700 px-6 py-3 font-bold text-white">
                Ver demonstração
              </button>
            </div>

            <div className="mt-10 grid max-w-lg grid-cols-3 gap-4 text-center">
              {[
                ["3.2k", "varreduras"],
                ["98.5%", "acurácia"],
                ["< 4 min", "tempo médio"],
              ].map(([value, label]) => (
                <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="text-2xl font-black text-[#14F195]">{value}</div>
                  <div className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-[#9945FF]/30 bg-gradient-to-br from-[#0b1226] via-[#0f172a] to-[#111827] p-5 shadow-2xl shadow-[#9945FF]/10">
            <div className="rounded-2xl border border-slate-700 bg-slate-950/80 p-5">
              <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-slate-400">
                <span>Simulador de varredura</span>
                <span className="text-[#14F195]">LIVE</span>
              </div>

              <div className="mt-6 space-y-4">
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                  <div className="text-xs text-slate-400">Alvo</div>
                  <div className="mt-1 font-medium">marciosouzagcm@gmail.com</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                  <div className="text-xs text-slate-400">Wallet correlacionada</div>
                  <div className="mt-1 font-medium break-all">0x9F4...A90c</div>
                </div>

                <div className="mt-5">
                  <div className="mb-2 flex justify-between text-xs uppercase tracking-[0.2em] text-slate-400">
                    <span>Progress</span>
                    <span>72%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full w-[72%] rounded-full bg-gradient-to-r from-[#9945FF] to-[#14F195]" />
                  </div>
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg bg-slate-900 p-3">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Achados</div>
                    <div className="mt-2 text-2xl font-black text-[#14F195]">18</div>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-3">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Risco</div>
                    <div className="mt-2 text-2xl font-black text-[#f59e0b]">ALTO</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="pricing" className="mt-16 grid gap-6 md:grid-cols-3">
          {[
            { name: 'Starter', price: 'USDC 19', description: '2 scans mensais, PDF básico e status executivo.', accent: 'border-slate-700' },
            { name: 'Pro', price: 'USDC 49', description: 'Análises avançadas e crédito de carteira correlacionada.', accent: 'border-[#9945FF]/60', highlight: true },
            { name: 'Enterprise', price: 'USDC 99', description: 'Trabalho por equipe, RBAC e SLA para compliance.', accent: 'border-[#14F195]/60' },
          ].map((plan) => (
            <div key={plan.name} className={`rounded-3xl border bg-slate-900/70 p-6 ${plan.accent} ${plan.highlight ? 'shadow-lg shadow-[#9945FF]/20' : ''}`}>
              <div className="text-xs uppercase tracking-[0.25em] text-slate-400">{plan.name}</div>
              <div className="mt-4 text-4xl font-black text-white">{plan.price}</div>
              <div className="mt-4 text-slate-300">{plan.description}</div>
              <button className={`mt-6 w-full rounded-full px-4 py-3 font-bold ${plan.highlight ? 'bg-gradient-to-r from-[#9945FF] to-[#14F195] text-slate-950' : 'border border-slate-700 text-white'}`}>
                Selecionar
              </button>
            </div>
          ))}
        </section>

        <section id="legal" className="mt-20 rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
          <div className="grid gap-8 md:grid-cols-2">
            <div>
              <div className="text-xs uppercase tracking-[0.3em] text-[#14F195]">Termos e compliance</div>
              <h2 className="mt-4 text-3xl font-black">Uso defensivo e proteção de dados.</h2>
            </div>
            <div className="space-y-3 text-sm text-slate-300">
              <p>Todos os dados de varredura são tratados de forma responsável e apenas com autorização explícita do titular ou da entidade consultada.</p>
              <p>O projeto inclui mascaramento de dados sensíveis, garantia de expurgo sob solicitação e política de privacidade aligned with LGPD/GDPR.</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
