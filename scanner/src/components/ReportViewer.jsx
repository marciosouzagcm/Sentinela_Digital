import React from 'react';
import { 
  Accordion, AccordionContent, AccordionItem, AccordionTrigger 
} from './ui/accordion';

const ReportViewer = ({ data }) => {
  if (!data || !data.categorias || Object.keys(data.categorias).length === 0) {
    return (
      <div className="p-6 border rounded-lg bg-white shadow-sm text-center">
        <h2 className="text-xl font-bold">Relatório: {data?.alvo}</h2>
        <p className="text-green-600 mt-2">✅ Nenhum risco crítico detectado no momento.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-xl shadow-lg border">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Relatório: {data.alvo}</h2>
      <Accordion type="single" collapsible className="w-full">
        {Object.entries(data.categorias).map(([categoria, achados], index) => (
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
                  <li key={i} className="p-3 bg-gray-50 rounded border-l-4 border-yellow-500">
                    <p className="font-bold text-gray-700">{item.nome}</p>
                    <p className="text-sm text-gray-600">{item.descricao}</p>
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
