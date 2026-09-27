import {
    Accordion, AccordionContent, AccordionItem, AccordionTrigger
} from './ui/accordion';

const severityStyles = {
  CRITICA: 'border-red-400/30 bg-red-400/10 text-red-200',
  ALTA: 'border-orange-400/30 bg-orange-400/10 text-orange-200',
  MEDIA: 'border-amber-300/30 bg-amber-300/10 text-amber-100',
  BAIXA: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200',
};

const metricStyles = {
  TOTAL: 'border-cyan-300/20 bg-cyan-300/[0.06] text-cyan-200',
  CRITICA: 'border-red-400/20 bg-red-400/[0.06] text-red-200',
  ALTA: 'border-orange-400/20 bg-orange-400/[0.06] text-orange-200',
  MEDIA: 'border-amber-300/20 bg-amber-300/[0.06] text-amber-100',
  BAIXA: 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200',
};

const ReportViewer = ({ data }) => {
  const metricas = data?.metricas || {};
  const categorias = Object.entries(data?.categorias || {}).filter(([, achados]) => Array.isArray(achados) && achados.length > 0);
  const total = Number(metricas.TOTAL ?? Object.values(metricas).reduce((s, v) => s + (Number(v) || 0), 0));

  if (!data) return null;

  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/65 p-5 shadow-xl shadow-black/20 sm:p-7">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Alvo analisado</p>
          <h3 className="mt-2 break-all text-xl font-bold text-white sm:text-2xl">{data.alvo || 'Alvo não informado'}</h3>
          <p className="mt-2 text-sm text-slate-400">URL / identificador: {data.alvo || 'não informado'}</p>
        </div>
        <div className="shrink-0 rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3 sm:text-right">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">Gerado em</p>
          <p className="mt-1 text-sm font-medium text-slate-200">{data.gerado_em || 'Data não informada'}</p>
        </div>
      </div>

      <div className={`my-5 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium ${Number(metricas.CRITICA || 0) === 0 ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : 'border-red-400/20 bg-red-400/[0.06] text-red-200'}`}>
        <span className={`h-2 w-2 rounded-full ${Number(metricas.CRITICA || 0) === 0 ? 'bg-emerald-300' : 'bg-red-300'}`} />
        {Number(metricas.CRITICA || 0) === 0 ? 'Nenhum risco crítico detectado' : `${metricas.CRITICA} risco(s) crítico(s) detectado(s)`}
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {['TOTAL', 'CRITICA', 'ALTA', 'MEDIA', 'BAIXA'].map((nivel) => (
          <div key={nivel} className={`rounded-2xl border p-4 ${metricStyles[nivel]}`}>
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] opacity-80">{nivel === 'CRITICA' ? 'Crítica' : nivel === 'MEDIA' ? 'Média' : nivel}</p>
            <p className="mt-2 text-3xl font-black tracking-tight">{Number(metricas[nivel]) || (nivel === 'TOTAL' ? total : 0)}</p>
            <p className="mt-1 text-xs opacity-60">{nivel === 'TOTAL' ? 'achados' : 'vulnerabilidades'}</p>
          </div>
        ))}
      </div>

      {total === 0 ? (
        <div className="rounded-2xl border border-emerald-400/15 bg-emerald-400/[0.04] px-5 py-8 text-center">
          <p className="font-semibold text-emerald-200">Nenhum achado detectado nesta varredura.</p>
          <p className="mt-1 text-sm text-slate-400">O alvo não apresentou vulnerabilidades nos indicadores monitorados.</p>
        </div>
      ) : categorias.length > 0 ? (
        <Accordion type="single" collapsible className="w-full">
          {categorias.map(([categoria, achados], index) => (
            <AccordionItem key={categoria} value={`item-${index}`} className="border-b border-white/10">
              <AccordionTrigger className="py-4 text-left text-base font-semibold text-slate-100 hover:no-underline">
                <span className="flex items-center gap-3">
                  {categoria}
                  <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-xs font-bold text-cyan-200">{achados.length}</span>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <ul className="space-y-3 pb-2">
                  {achados.map((item, i) => {
                    const severity = item.severidade?.toUpperCase() || 'MEDIA';
                    const severityClass = severityStyles[severity] || 'border-slate-500/30 bg-slate-500/10 text-slate-200';
                    return (
                      <li key={`${categoria}-${i}`} className={`rounded-xl border p-4 ${severityClass}`}>
                        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                          <p className="font-semibold">{item.titulo || item.nome || 'Achado de segurança'}</p>
                          <span className="rounded-full border border-current/20 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider">{item.severidade || 'Média'}</span>
                        </div>
                        {item.descricao ? <p className="text-sm leading-relaxed text-slate-300">{item.descricao}</p> : null}
                        {item.mitigacao ? <p className="mt-3 border-t border-white/10 pt-3 text-sm leading-relaxed text-cyan-100"><span className="font-semibold text-cyan-300">Mitigação: </span>{item.mitigacao}</p> : null}
                      </li>
                    );
                  })}
                </ul>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      ) : null}
    </div>
  );
};

export default ReportViewer;
