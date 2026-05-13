import React, { useState } from 'react';
import { BASE_URL } from '../api/client';
import { FileDown, Maximize2, Edit3 } from 'lucide-react';
import CVEditorModal from './CVEditorModal';

const CVPreview = ({ companyId, score }) => {
  const [timestamp, setTimestamp] = useState(Date.now());
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const pdfUrl = `${BASE_URL}/generation/cv/${companyId}?t=${timestamp}`;
  
  const getScoreColor = (s) => {
    if (s >= 9.0) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/50";
    if (s >= 7.0) return "bg-amber-500/20 text-amber-400 border-amber-500/50";
    return "bg-red-500/20 text-red-400 border-red-500/50";
  };

  return (
    <div className="w-full h-full flex flex-col gap-3 relative group">
      
      {/* Floating score badge */}
      <div className={`absolute -top-3 -right-3 px-3 py-1 bg-zinc-900 border rounded-full text-xs font-bold shadow-xl z-10 ${getScoreColor(score)}`}>
        {score.toFixed(1)}/10
      </div>

      {/* PDF Viewport Fake / Iframe Wrapper */}
      <div className="relative w-full h-[300px] rounded-xl overflow-hidden shadow-2xl border border-zinc-700 bg-white">
         <iframe 
           key={`iframe-${timestamp}`}
           src={`${pdfUrl}#toolbar=0&navpanes=0&scrollbar=0`} 
           onLoad={() => setIsRefreshing(false)}
           className={`w-full h-full pointer-events-none transition-all duration-500 ${isRefreshing ? 'opacity-20 blur-sm' : 'opacity-90 group-hover:opacity-100'}`}
           title={`CV for ${companyId}`}
         />
         
         {isRefreshing && (
           <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-[2px]">
             <div className="flex flex-col items-center gap-2">
                <div className="w-8 h-8 border-4 border-[#6C63FF] border-t-transparent rounded-full animate-spin" />
                <span className="text-xs font-bold text-zinc-800 bg-white/80 px-2 py-0.5 rounded shadow-sm">Refreshing PDF...</span>
             </div>
           </div>
         )}
         
         {/* Overlay Hover Actions */}
         <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-4 backdrop-blur-sm">
             <button 
               key={`edit-${timestamp}`}
               onClick={() => setIsEditorOpen(true)}
               className="p-3 bg-amber-500 hover:bg-amber-600 text-white rounded-full transition-transform hover:scale-110 shadow-lg"
               title="Edit Source"
             >
                <Edit3 className="w-5 h-5" />
             </button>
             <a 
               key={`max-${timestamp}`}
               href={pdfUrl} 
               target="_blank" 
               rel="noreferrer"
               className="p-3 bg-[#6C63FF] hover:bg-[#5B54E6] text-white rounded-full transition-transform hover:scale-110 shadow-lg"
               title="Open full screen"
             >
                <Maximize2 className="w-5 h-5" />
             </a>
             <a 
               key={`dl-${timestamp}`}
               href={pdfUrl} 
               download={`CV_${companyId}_${timestamp}.pdf`}
               className="p-3 bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 text-white rounded-full transition-transform hover:scale-110 shadow-lg"
               title="Download PDF"
             >
                <FileDown className="w-5 h-5" />
             </a>
          </div>
       </div>

        {isEditorOpen && (
          <CVEditorModal 
            companyId={companyId} 
            docType="cv" 
            onClose={() => setIsEditorOpen(false)}
            onSaveSuccess={(shouldClose = true) => {
              setTimestamp(Date.now());
              setIsRefreshing(true);
              if (shouldClose) setIsEditorOpen(false);
            }}
          />
        )}
    </div>
  );
};

export default CVPreview;
