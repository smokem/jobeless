import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import ChatWindow from '../components/ChatWindow';
import HelpOverlay from '../components/HelpOverlay';
import { PlayCircle, Target, Loader2, LifeBuoy, StopCircle, RefreshCw, Send, CheckCircle2 } from 'lucide-react';

const Interview = () => {
  const [targets, setTargets] = useState([]);
  const [activeCompany, setActiveCompany] = useState(null);
  const [session, setSession] = useState(null); // { session_id, messages: [] }
  const [sessionsHistory, setSessionsHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Chat state
  const [inputMsg, setInputMsg] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  
  // Coaching State
  const [coachData, setCoachData] = useState(null);
  const [isCoaching, setIsCoaching] = useState(false);
  
  // Score block
  const [scoreData, setScoreData] = useState(null);
  
  useEffect(() => {
     apiClient.getTargets().then(t => {
         setTargets(t.filter(target => target.status !== 'ignored'));
         setLoading(false);
     });
  }, []);

  const loadHistory = async (companyId) => {
      try {
          const s = await apiClient.request(`/interview/${companyId}/sessions`);
          setSessionsHistory(s);
      } catch (e) { console.error(e); }
  };

  const handleSelectCompany = (companyId) => {
     setActiveCompany(targets.find(t => t.company_id === companyId));
     setSession(null);
     setScoreData(null);
     loadHistory(companyId);
  };

  const handleStartSession = async () => {
      setIsTyping(true);
      setScoreData(null);
      setSession({ session_id: 'loading', messages: [] });
      
      try {
          const newSession = await apiClient.startInterviewSession(activeCompany.company_id);
          setSession(newSession);
          loadHistory(activeCompany.company_id);
      } catch (e) {
          console.error("Failed to start session", e);
      } finally {
          setIsTyping(false);
      }
  };

  const handleSendMessage = async (e) => {
      if (e) e.preventDefault();
      if (!inputMsg.trim() || !session || isTyping) return;
      
      const msg = inputMsg;
      setInputMsg("");
      const localMsg = { role: "user", content: msg };
      
      // Optimistic update
      setSession(prev => ({ ...prev, messages: [...prev.messages, localMsg] }));
      setIsTyping(true);
      
      try {
          const resp = await apiClient.sendInterviewMessage(activeCompany.company_id, session.session_id, msg);
          setSession(prev => ({ 
             ...prev, 
             messages: [...prev.messages, { role: "assistant", content: resp.reply }] 
          }));
      } catch (err) {
          console.error(err);
      } finally {
          setIsTyping(false);
      }
  };

  const handleHelpMe = async () => {
      if (!session || isTyping || isCoaching) return;
      setIsCoaching(true);
      try {
          const coaching = await apiClient.request(`/interview/${activeCompany.company_id}/${session.session_id}/help`, { method: "POST" });
          setCoachData(coaching);
      } catch (err) {
          console.error(err);
      } finally {
          setIsCoaching(false);
      }
  };

  const handleEndSession = async () => {
      if (!session || isTyping) return;
      setIsTyping(true);
      try {
          const score = await apiClient.endInterviewSession(activeCompany.company_id, session.session_id);
          setScoreData(score);
          setSession(null); // Clear chat box, show score card
          loadHistory(activeCompany.company_id);
      } catch (err) {
          console.error(err);
      } finally {
          setIsTyping(false);
      }
  };

  const handleResetCompany = async () => {
      try {
          await apiClient.request(`/interview/${activeCompany.company_id}/sessions`, { method: "DELETE" });
          setSessionsHistory([]);
          setSession(null);
          setScoreData(null);
      } catch (err) { console.error(err); }
  };

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="w-8 animate-spin text-[#6C63FF]" /></div>;

  return (
    <div className="max-w-[1400px] mx-auto h-[calc(100vh-100px)] flex gap-6 pb-6">
      
      {/* Left Panel: Navigation & History */}
      <div className="w-[30%] min-w-[300px] bg-zinc-900 border border-zinc-800 rounded-2xl p-5 flex flex-col h-full">
         <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Target className="w-5 h-5 text-emerald-400" /> Target Practice
         </h2>
         
         <div className="space-y-2 mb-6 max-h-[30%] overflow-y-auto custom-scrollbar">
            {targets.map(t => (
               <button 
                  key={t.company_id}
                  onClick={() => handleSelectCompany(t.company_id)}
                  className={`w-full text-left p-3 rounded-xl border transition ${
                     activeCompany?.company_id === t.company_id ? 'bg-[#6C63FF]/20 border-[#6C63FF] text-white' : 'bg-zinc-950/50 border-zinc-800 text-zinc-400 hover:border-zinc-600'
                  }`}
               >
                  <p className="font-bold truncate">{t.company_name}</p>
                  <p className="text-xs opacity-70 truncate">{t.job_title}</p>
               </button>
            ))}
         </div>

         {activeCompany && (
             <div className="flex-1 flex flex-col border-t border-zinc-800/60 pt-6">
                 <div className="flex justify-between items-center mb-4">
                     <h3 className="font-bold text-white text-sm">Session History</h3>
                     <button onClick={handleResetCompany} className="text-red-400 text-xs hover:underline flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" /> Reset
                     </button>
                 </div>
                 
                 <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar">
                    {sessionsHistory.length === 0 && <p className="text-zinc-500 text-xs italic">No past sessions.</p>}
                    {sessionsHistory.map((s, i) => (
                       <div key={i} className="px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-sm text-zinc-300 font-mono flex items-center gap-2">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Session {s.session_id.split('-')[0]}
                       </div>
                    ))}
                 </div>
                 
                 {(!session && !scoreData) && (
                     <button 
                        onClick={handleStartSession}
                        className="mt-4 w-full py-3 bg-[#6C63FF] hover:bg-[#5B54E6] text-white font-bold rounded-xl flex justify-center items-center gap-2 transition shadow-lg"
                     >
                        <PlayCircle className="w-5 h-5"/> Start New Session
                     </button>
                 )}
                 {scoreData && (
                     <button 
                        onClick={() => { setScoreData(null); handleStartSession(); }}
                        className="mt-4 w-full py-3 bg-zinc-800 hover:bg-zinc-700 text-white font-bold rounded-xl flex justify-center items-center gap-2 transition"
                     >
                        <RefreshCw className="w-4 h-4"/> Try Again
                     </button>
                 )}
             </div>
         )}
      </div>

      {/* Right Panel: Active Chat / Score View */}
      <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden relative flex flex-col shadow-xl">
         {!activeCompany ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
               <Target className="w-12 h-12 mb-4 opacity-30" />
               <p className="text-lg">Select a target company to begin simulation.</p>
            </div>
         ) : session ? (
            <>
               <div className="bg-zinc-950 border-b border-zinc-800 p-4 flex justify-between items-center z-10 shrink-0 shadow-lg">
                   <div>
                       <h3 className="text-white font-bold tracking-wide">Live Interview: {activeCompany.company_name}</h3>
                       <p className="text-xs text-emerald-400 font-mono mt-1">Status: Active</p>
                   </div>
                   <div className="flex gap-3">
                       <button 
                          onClick={handleHelpMe} 
                          disabled={isCoaching || isTyping}
                          className="px-4 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 border border-amber-500/30 rounded-lg text-sm font-bold flex items-center gap-2 transition disabled:opacity-50"
                       >
                          {isCoaching ? <Loader2 className="w-4 h-4 animate-spin"/> : <LifeBuoy className="w-4 h-4"/>} Coach
                       </button>
                       <button 
                          onClick={handleEndSession} 
                          disabled={isTyping}
                          className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-bold flex items-center gap-2 transition disabled:opacity-50 shadow-lg shadow-red-500/20"
                       >
                          <StopCircle className="w-4 h-4" /> End Session
                       </button>
                   </div>
               </div>
               
               <ChatWindow messages={session.messages} isTyping={isTyping} />
               
               <form onSubmit={handleSendMessage} className="p-4 bg-zinc-950 border-t border-zinc-800 shrink-0">
                  <div className="relative">
                      <input 
                         type="text" 
                         value={inputMsg}
                         onChange={e => setInputMsg(e.target.value)}
                         disabled={isTyping || isCoaching}
                         placeholder="Type your response... (Enter to send)"
                         className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-5 py-4 text-white placeholder-zinc-500 focus:outline-none focus:border-[#6C63FF] transition pr-16"
                      />
                      <button 
                         type="submit" 
                         disabled={!inputMsg.trim() || isTyping}
                         className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-[#6C63FF] hover:bg-[#5B54E6] text-white rounded-lg disabled:opacity-50 disabled:bg-zinc-700 transition"
                      >
                         <Send className="w-4 h-4" />
                      </button>
                  </div>
               </form>
               
               {/* Overlay */}
               {coachData && <HelpOverlay data={coachData} onClose={() => setCoachData(null)} />}
            </>
         ) : scoreData ? (
             <div className="flex-1 flex flex-col p-8 overflow-y-auto custom-scrollbar animate-in fade-in slide-in-from-bottom-8">
                 <h2 className="text-3xl font-bold text-white mb-2">Interview Evaluation</h2>
                 <p className="text-zinc-400 mb-8">Performance breakdown against {activeCompany.company_name} requirements.</p>

                 <div className="flex gap-6 mb-8">
                     <div className={`shrink-0 w-40 h-40 rounded-[2rem] flex flex-col items-center justify-center border-4 ${scoreData.overall_score >= 8 ? 'border-emerald-500 bg-emerald-500/10' : scoreData.overall_score >= 6 ? 'border-amber-500 bg-amber-500/10' : 'border-red-500 bg-red-500/10'}`}>
                         <span className={`text-5xl font-black ${scoreData.overall_score >= 8 ? 'text-emerald-400' : scoreData.overall_score >= 6 ? 'text-amber-400' : 'text-red-400'}`}>{scoreData.overall_score}</span>
                         <span className="text-zinc-500 font-bold mt-1 text-sm">/ 10</span>
                     </div>
                     <div className="flex-1 grid grid-cols-2 gap-4">
                         {Object.entries(scoreData.categories).map(([k, v]) => (
                             <div key={k} className="bg-zinc-950 border border-zinc-800 p-4 rounded-xl">
                                 <h4 className="text-zinc-500 uppercase tracking-wider text-[10px] font-bold mb-2">{k.replace('_', ' ')}</h4>
                                 <div className="w-full bg-zinc-900 rounded-full h-2">
                                     <div className={`h-2 rounded-full ${v >= 8 ? 'bg-emerald-400' : v >= 6 ? 'bg-amber-400' : 'bg-red-400'}`} style={{ width: `${(v/10)*100}%` }}></div>
                                 </div>
                                 <p className="text-white font-mono mt-2 text-sm">{v}/10</p>
                             </div>
                         ))}
                     </div>
                 </div>

                 <div className="grid grid-cols-2 gap-6 mb-6">
                     <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
                         <h3 className="text-emerald-400 font-bold mb-4 flex items-center gap-2"><CheckCircle2 className="w-5 h-5"/> Strengths</h3>
                         <ul className="space-y-3">
                             {scoreData.strengths.map((s,i) => <li key={i} className="text-zinc-300 text-sm flex gap-2"><span className="text-emerald-500 mt-0.5">•</span> {s}</li>)}
                         </ul>
                     </div>
                     <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-6">
                         <h3 className="text-amber-400 font-bold mb-4 flex items-center gap-2"><Target className="w-5 h-5"/> Areas to Improve</h3>
                         <ul className="space-y-3">
                             {scoreData.improvements.map((s,i) => <li key={i} className="text-zinc-300 text-sm flex gap-2"><span className="text-amber-500 mt-0.5">•</span> {s}</li>)}
                         </ul>
                     </div>
                 </div>
                 
                 <div className="bg-zinc-900 p-6 rounded-xl border border-zinc-800 flex items-center justify-between">
                     <div>
                        <h4 className="text-white font-bold text-lg">AI Recommendation</h4>
                        <p className="text-zinc-400 text-sm">Based purely on transcript.</p>
                     </div>
                     <span className={`px-6 py-2 rounded-full font-black uppercase tracking-widest ${scoreData.recommendation.toLowerCase() === 'hire' ? 'bg-emerald-500 text-white' : scoreData.recommendation.toLowerCase() === 'consider' ? 'bg-amber-500 text-white' : 'bg-red-500 text-white'}`}>
                        {scoreData.recommendation}
                     </span>
                 </div>
             </div>
         ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500 animate-in fade-in">
               <Target className="w-16 h-16 mb-4 opacity-50 text-[#6C63FF]" />
               <h2 className="text-2xl font-bold text-white mb-2">Ready to Practice</h2>
               <p className="text-center max-w-md">Hit "Start New Session" on the left to begin simulating a real interview parameterized specifically to the chosen company.</p>
            </div>
         )}
      </div>
    </div>
  );
};

export default Interview;
