import React from 'react';

const StatusIndicator = ({ lastUpdate }) => {
  const isOnline = lastUpdate !== null;

  return (
    <div className="flex items-center gap-2 bg-white px-3 py-1 rounded-full border shadow-sm">
      <div className="relative flex h-3 w-3">
        {isOnline && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
        )}
        <span className={`relative inline-flex rounded-full h-3 w-3 ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}></span>
      </div>
      <span className="text-sm font-medium text-gray-700">
        {isOnline ? "Sistema Ativo" : "Sistema Offline"}
      </span>
    </div>
  );
};

export default StatusIndicator;
