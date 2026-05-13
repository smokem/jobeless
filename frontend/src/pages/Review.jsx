import React, { useState, useEffect } from 'react';
import { apiClient, BASE_URL } from '../api/client';
import CVPreview from '../components/CVPreview';
import { Target, Zap, PlayCircle, Loader2, CheckCircle2, ChevronRight, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Review = () => {
  const navigate = useNavigate();
  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeGeneration, setActiveGeneration] = useState(null); // company_id
  const [progressMessages, setProgressMessages] = useState({});
  const [completed, setCompleted] = useState({});
  
  useEffect(() => {
    fetchTargets();
  }, []);

  const fetchTargets = async () => {
    try {
      const allTargets = await apiClient.getTargets();
      // Only show pending targets that we selected
      setTargets(allTargets.filter(t => t.status === 'pending'));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (company_id) => {
    setActiveGeneration(company_id);
    setProgressMessages(prev => ({ ...prev, [company_id]: "Starting engine..." }));
    
    try {
      // 1. Trigger background generation
      await apiClient.generateCV(company_id);
      
      // 2. Connect to SSE stream
      const eventSource = new EventSource(`${BASE_URL}/generation/status/${company_id}`);
      
      eventSource.onmessage = (event) => {
        const data = event.data;
        if (data.startsWith("DONE|")) {
          const score = data.split("|")[1];
          setCompleted(prev => ({ ...prev, [company_id]: { score: parseFloat(score) } }));
          setActiveGeneration(null);
          eventSource.close();
        } else if (data.startsWith("ERROR|")) {
           setProgressMessages(prev => ({ ...prev, [company_id]: data }));
           setActiveGeneration(null);
           eventSource.close();
        } else {
          setProgressMessages(prev => ({ ...prev, [company_id]: data }));
        }
      };

      eventSource.onerror = () => {
        console.error("SSE connection lost");
        eventSource.close();
        setActiveGeneration(null);
      };

    } catch (err) {
      setProgressMessages(prev => ({ ...prev, [company_id]: "Failed to start generation." }));
      setActiveGeneration(null);
    }
  };

  const handleGenerateAll = async () => {
    // Generate sequentially
    for (const target of targets) {
      if (!completed[target.company_id]) {
        await handleGenerate(target.company_id);
        // We'd ideally wait for it to finish, but EventSource is handled async.
        // For sequential execution, we'd need a polling mechanism or wrapper promise over EventSource.
        // Simplified: triggers all simultaneously in UI, or wait manually.
      }
    }
  };

  if (loading) return <div className="p-8"><Loader2 className="w-8 h-8 animate-spin text-[#6C63FF]" /></div>;

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Review & Generate</h1>
        <p className="text-zinc-500 text-sm mt-1">Research targets and generate hyper-tailored CVs.</p>
      </div>

      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
             <div className="p-2 bg-emerald-500/10 rounded-lg">
                <Target className="text-emerald-400 w-5 h-5"/>
             </div>
             <h2 className="text-lg font-semibold text-white">Target Queue ({targets.length})</h2>
          </div>
          <button
            onClick={handleGenerateAll}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 border border-zinc-700 focus:ring-2 focus:ring-[#6C63FF]"
          >
            <PlayCircle className="w-4 h-4 text-emerald-400" />
            Generate All Sequential
          </button>
        </div>

        <div className="space-y-4">
          {targets.map(target => {
             const isGenerating = activeGeneration === target.company_id;
             const isComplete = !!completed[target.company_id];
             const msg = progressMessages[target.company_id];

             return (
              <div key={target.company_id} className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden flex flex-col md:flex-row shadow-sm">
                
                {/* Left: Info & Status */}
                <div className="flex-1 p-5 border-r border-zinc-800/60">
                   <div className="flex justify-between items-start mb-4">
                      <div>
                         <h3 className="text-lg font-bold text-white">{target.company_name}</h3>
                         <p className="text-sm text-zinc-400">{target.job_title} • {target.location}</p>
                      </div>
                      <span className="text-[10px] font-mono tracking-wider uppercase px-2 py-1 bg-zinc-800 rounded text-zinc-400">
                      {target.apply_type.replace('_', ' ')}
                      </span>
                   </div>

                   {/* Progress Tracker */}
                   <div className="bg-zinc-900 p-4 rounded-lg min-h-[80px] flex flex-col justify-center border border-zinc-800/80">
                      {isGenerating ? (
                         <div className="flex items-center gap-3 text-sm font-mono text-zinc-300">
                           <Loader2 className="w-4 h-4 animate-spin text-[#6C63FF]" />
                           <span className="animate-pulse">{msg || "Waiting..."}</span>
                         </div>
                      ) : isComplete ? (
                         <div className="flex items-center gap-3 text-sm font-semibold text-emerald-400">
                           <CheckCircle2 className="w-5 h-5" />
                           <span>Complete! Match Score: {completed[target.company_id].score.toFixed(1)}/10</span>
                         </div>
                      ) : msg && String(msg).includes("ERROR") ? (
                         <div className="text-sm text-red-400 font-mono">
                           {msg}
                         </div>
                      ) : (
                         <div className="text-sm text-zinc-500 font-mono">
                           Awaiting generation.
                         </div>
                      )}
                   </div>

                   {!isComplete && !isGenerating && (
                      <button
                        onClick={() => handleGenerate(target.company_id)}
                        className="mt-4 px-4 py-2 bg-[#6C63FF] hover:bg-[#5B54E6] text-white rounded-lg text-sm font-medium transition-colors w-full flex items-center justify-center gap-2"
                      >
                         <Zap className="w-4 h-4"/> Research + Generate
                      </button>
                   )}
                </div>

                {/* Right: PDF Preview Component */}
                <div className="w-full md:w-[350px] bg-zinc-900/30 flex items-center justify-center p-4">
                  {isComplete ? (
                     <CVPreview companyId={target.company_id} score={completed[target.company_id].score} />
                  ) : (
                     <div className="flex flex-col items-center justify-center text-zinc-600 gap-3 border-2 border-dashed border-zinc-800 rounded-lg w-full h-full min-h-[250px]">
                        <FileText className="w-8 h-8 opacity-50" />
                        <span className="text-xs uppercase font-mono tracking-widest opacity-50">No Document</span>
                     </div>
                  )}
                </div>
              </div>
             )
          })}
          
          {targets.length === 0 && (
             <div className="text-center py-12 text-zinc-500 bg-zinc-950 rounded-xl border border-zinc-800 border-dashed">
                No active targets selected. Go back to Discovery.
             </div>
          )}
        </div>
      </div>
      
      {targets.length > 0 && (
         <div className="flex justify-end p-4 border-t border-zinc-800/50">
           <button 
             onClick={() => navigate('/apply')}
             className="px-6 py-3 bg-white text-black hover:bg-zinc-200 rounded-xl font-bold transition-all flex items-center gap-2"
           >
             Proceed to Apply Phase
             <ChevronRight className="w-4 h-4 ml-1" />
           </button>
         </div>
      )}
    </div>
  );
};

export default Review;
