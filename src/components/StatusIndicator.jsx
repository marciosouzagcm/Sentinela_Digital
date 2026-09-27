
const StatusIndicator = ({ lastUpdate, online }) => {
  const isOnline = online ?? lastUpdate !== null;

  return (
    <div className="flex items-center gap-2 rounded-full border border-white/10 bg-slate-900/80 px-3 py-2 shadow-sm">
      <div className="relative flex h-3 w-3">
        {isOnline && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-50"></span>
        )}
        <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
      </div>
      <span className="text-xs font-medium text-slate-300">
        {isOnline ? 'Sistema ativo' : 'Sistema offline'}
      </span>
    </div>
  );
};

export default StatusIndicator;
