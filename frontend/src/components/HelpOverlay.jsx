import React from 'react';
import { X, Target, Lightbulb, KeyRound } from 'lucide-react';

const HelpOverlay = ({ data, onClose }) => {
  if (!data) return null;

  return (
    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-in fade-in duration-200">
      <div className="bg-zinc-950 border border-amber-500/30 shadow-2xl shadow-black rounded-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90%]">
        
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
               <Lightbulb className="w-5 h-5 text-amber-400" />
               <h3 className="text-white font-bold tracking-wide">Coach Insights</h3>
            </div>
            <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg text-zinc-400 transition">
               <X className="w-5 h-5" />
            </button>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">
           
           <div>
              <div className="flex items-center gap-2 mb-2">
                 <Target className="w-4 h-4 text-emerald-400" />
                 <h4 className="text-sm font-semibold text-emerald-400 uppercase tracking-widest">What They Really Mean</h4>
              </div>
              <p className="text-sm text-zinc-300 p-3 bg-zinc-900 rounded-xl border border-zinc-800">
                 {data.question_intent}
              </p>
           </div>
           
           <div>
              <div className="flex items-center gap-2 mb-2">
                 <div className="w-4 h-4 rounded text-[10px] font-bold bg-[#6C63FF] text-white flex items-center justify-center">123</div>
                 <h4 className="text-sm font-semibold text-[#6C63FF] uppercase tracking-widest">Answer Structure</h4>
              </div>
              <div className="text-sm text-zinc-300 p-3 bg-zinc-900 rounded-xl border border-zinc-800 whitespace-pre-wrap">
                 {data.ideal_answer_structure}
              </div>
           </div>

           <div>
              <div className="flex items-center gap-2 mb-2">
                 <KeyRound className="w-4 h-4 text-amber-400" />
                 <h4 className="text-sm font-semibold text-amber-400 uppercase tracking-widest">Keywords to Hit</h4>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                  {data.keywords_to_mention?.map((kw, i) => (
                     <span key={i} className="px-3 py-1 bg-zinc-800 text-amber-300 text-xs font-mono rounded-full border border-amber-500/20 shadow-sm">{kw}</span>
                  ))}
              </div>
           </div>
           
           <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-[#6C63FF] opacity-10 rounded-xl"></div>
              <div className="p-4 border border-zinc-700/50 rounded-xl relative">
                 <span className="absolute -top-3 left-4 bg-zinc-950 px-2 text-[10px] font-bold uppercase tracking-wider text-zinc-500">Pro Tip</span>
                 <p className="text-sm font-medium text-white italic">"{data.coaching_tip}"</p>
              </div>
           </div>

        </div>

      </div>
    </div>
  );
};

export default HelpOverlay;
