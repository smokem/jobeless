import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { Send, AlertTriangle, CheckCircle2, XCircle, Loader2, StopCircle, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Apply = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Execution state
  const [isRunning, setIsRunning] = useState(false);
  const [progressLog, setProgressLog] = useState([]); // [{company_id, name, status, error}]
  const abortController = useRef(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const stats = await apiClient.getApplyStatus();
      setStatus(stats);
      
      const allTargets = await apiClient.getTargets();
      setTargets(allTargets.filter(t => t.status === 'pending'));
    } catch (err) {
      console.error("Failed to load apply status", err);
    } finally {
      setLoading(false);
    }
  };

  const addLog = (companyId, name, logStatus, error = null) => {
    setProgressLog(prev => {
       const existing = prev.findIndex(p => p.company_id === companyId);
       const entry = { company_id: companyId, name, status: logStatus, error };
       if (existing >= 0) {
          const newLogs = [...prev];
          newLogs[existing] = entry;
          return newLogs;
       }
       return [entry, ...prev];
    });
  };

  const handleStartQueue = async () => {
    if (targets.length === 0) return;
    setIsRunning(true);
    abortController.current = false;
    
    let sentCount = status.sent_today;

    for (const target of targets) {
      if (abortController.current) {
         addLog(target.company_id, target.company_name, "aborted");
         break;
      }
      
      if (sentCount >= status.max_limit) {
         addLog(target.company_id, target.company_name, "error", "Daily limit reached.");
         break;
      }

      addLog(target.company_id, target.company_name, "processing");

      try {
        await apiClient.applyToCompany(target.company_id);
        addLog(target.company_id, target.company_name, "success");
        sentCount++;
      } catch (err) {
        addLog(target.company_id, target.company_name, "error", err.message || "Failed to apply");
      }
      
      // Artificial delay between requests to be safe
      await new Promise(r => setTimeout(r, 2000));
    }
    
    setIsRunning(false);
    fetchData(); // Refresh limits
  };

  const handleAbort = () => {
    abortController.current = true;
    setIsRunning(false);
  };

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="w-8 h-8 animate-spin text-[#6C63FF]" /></div>;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Auto Apply Queue</h1>
        <p className="text-zinc-500 text-sm mt-1">Submit prepared applications automatically.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
         <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-zinc-400 mb-1">Queue Size</h3>
            <p className="text-3xl font-bold text-white">{targets.length}</p>
         </div>
         <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-zinc-400 mb-1">Sent Today</h3>
            <p className="text-3xl font-bold text-emerald-400">{status?.sent_today} <span className="text-sm text-zinc-500">/ {status?.max_limit}</span></p>
         </div>
         <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-zinc-400 mb-1">Remaining Allowance</h3>
            <p className="text-3xl font-bold text-[#6C63FF]">{status?.remaining_today}</p>
         </div>
      </div>

      {status?.remaining_today < targets.length && targets.length > 0 && (
         <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start gap-3">
             <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
             <p className="text-sm text-amber-200">
               Your queue ({targets.length}) exceeds your remaining daily limit ({status.remaining_today}).
               The queue will automatically pause once the limit is reached to protect your account standing.
             </p>
         </div>
      )}

      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden p-6 shadow-sm">
         <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white">Execution Log</h2>
            <div className="flex gap-3">
               {!isRunning && (
                  <button
                    onClick={handleStartQueue}
                    disabled={targets.length === 0 || status?.remaining_today <= 0}
                    className="px-6 py-2 bg-[#6C63FF] hover:bg-[#5B54E6] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-bold transition flex items-center gap-2"
                  >
                     <Send className="w-4 h-4" /> Start Apply Queue
                  </button>
               )}
               {isRunning && (
                  <button
                    onClick={handleAbort}
                    className="px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-bold transition flex items-center gap-2 shadow-lg shadow-red-500/20"
                  >
                     <StopCircle className="w-4 h-4" /> Abort execution
                  </button>
               )}
            </div>
         </div>

         <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
            {progressLog.length === 0 && (
               <div className="text-center py-10 text-zinc-600 font-mono text-sm border border-zinc-800 border-dashed rounded-xl">
                 Awaiting execution...
               </div>
            )}
            
            {progressLog.map((log, idx) => (
               <div key={idx} className={`p-4 rounded-xl border flex items-center justify-between ${
                 log.status === 'processing' ? 'bg-[#6C63FF]/10 border-[#6C63FF]/30' :
                 log.status === 'success' ? 'bg-emerald-500/10 border-emerald-500/30' :
                 log.status === 'error' ? 'bg-red-500/10 border-red-500/30' :
                 'bg-zinc-900/50 border-zinc-800'
               }`}>
                  <div className="flex items-center gap-3">
                     {log.status === 'processing' && <Loader2 className="w-5 h-5 text-[#6C63FF] animate-spin" />}
                     {log.status === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                     {log.status === 'error' && <XCircle className="w-5 h-5 text-red-400" />}
                     {log.status === 'aborted' && <StopCircle className="w-5 h-5 text-zinc-400" />}
                     
                     <div>
                        <h4 className="text-white font-medium">{log.name}</h4>
                        {log.error && <p className="text-xs text-red-400 mt-1">{log.error}</p>}
                     </div>
                  </div>
                  
                  <div className="text-xs font-mono uppercase tracking-widest text-zinc-500">
                     {log.status}
                  </div>
               </div>
            ))}
         </div>
      </div>
      
      {!isRunning && progressLog.length > 0 && (
          <div className="flex justify-end p-4">
             <button
               onClick={() => navigate('/')}
               className="px-6 py-3 bg-white hover:bg-zinc-200 text-black rounded-xl font-bold transition flex items-center gap-2"
             >
               Return to Dashboard
             </button>
          </div>
      )}
    </div>
  );
};

export default Apply;
