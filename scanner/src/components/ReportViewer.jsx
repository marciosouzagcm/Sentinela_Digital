import {
    Accordion, AccordionContent, AccordionItem, AccordionTrigger
} from './ui/accordion';

const severityStyles = {
  CRITICA: 'bg-red-100 text-red-800 border-red-500',
  ALTA: 'bg-orange-100 text-orange-800 border-orange-500',
  MEDIA: 'bg-yellow-100 text-yellow-800 border-yellow-500',
  BAIXA: 'bg-green-100 text-green-800 border-green-500',
};

const ReportViewer = ({ data }) => {
  const metricas = data?.metricas || {};
  const categorias = Object.entries(data?.categorias || {}).filter(([, achados]) => Array.isArray(achados) && achados.length > 0);
  const total = Number(metricas.TOTAL ?? Object.values(metricas).reduce((s, v) => s + (Number(v) || 0), 0));

  if (!data) return null;

  if (total === 0) {
    return (
      <div className="p-6 border rounded-lg bg-white shadow-sm text-center">
        <h2 className="text-xl font-bold">Relatório: {data?.alvo || 'Sem alvo'}</h2>
        <p className="text-green-600 mt-2">✅ Nenhum achado detectado no momento.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-xl shadow-lg border">
      <h2 className="text-2xl font-bold mb-2 text-gray-800">Relatório: {data.alvo}</h2>
      <p className="text-sm text-gray-500 mb-2">URL escaneada: {data.alvo || 'não informada'}</p>
      <p className="text-sm text-gray-500 mb-2">Gerado em {data.gerado_em || 'não informado'}</p>
      {Number(metricas.CRITICA || 0) === 0 ? (
        <p className="text-green-600 mb-4">✅ Nenhum risco crítico detectado no momento.</p>
      ) : (
        <p className="text-red-600 mb-4">⚠️ {metricas.CRITICA} risco(s) crítico(s) detectado(s).</p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {['TOTAL', 'CRITICA', 'ALTA', 'MEDIA', 'BAIXA'].map((nivel) => (
          <div key={nivel} className="rounded-lg border bg-gray-50 p-3 text-center">
            <p className="text-xs uppercase text-gray-500">{nivel}</p>
            <p className="text-xl font-bold text-gray-800">{metricas[nivel] ?? 0}</p>
          </div>
        ))}
      </div>

      <Accordion type="single" collapsible className="w-full">
        {categorias.map(([categoria, achados], index) => (
          <AccordionItem key={index} value={`item-${index}`}>
            <AccordionTrigger className="text-lg font-semibold hover:no-underline">
              <span className="flex items-center gap-2">
                {categoria}
                <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                  {achados.length}
                </span>
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <ul className="space-y-3">
                {achados.map((item, i) => (
                  <li key={i} className={`p-3 bg-gray-50 rounded border-l-4 ${severityStyles[item.severidade?.toUpperCase()] || 'border-gray-500'}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-bold text-gray-700">{item.titulo || item.nome}</p>
                      <span className={`text-xs px-2 py-1 rounded-full ${severityStyles[item.severidade?.toUpperCase()] || 'bg-gray-100 text-gray-800'}`}>
                        {item.severidade || 'MEDIA'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{item.descricao}</p>
                    {item.mitigacao ? <p className="text-sm text-blue-700 mt-2">Mitigação: {item.mitigacao}</p> : null}
                  </li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
};

export default ReportViewer;
