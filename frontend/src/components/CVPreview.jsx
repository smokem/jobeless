import React, { useState } from 'react';
import { BASE_URL } from '../api/client';
import { FileDown, Maximize2, X, RefreshCw, AlertCircle } from 'lucide-react';

const CVPreview = ({ companyId, score = null, docType = "cv", onRegenerate }) => {
  const [timestamp, setTimestamp] = useState(Date.now());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenError, setRegenError] = useState(null);

  const handleRegenerate = async () => {
    if (!onRegenerate || isRegenerating) return;
    setIsRegenerating(true);
    setRegenError(null);
    try {
      await onRegenerate();
      setTimestamp(Date.now());
    } catch (err) {
      setRegenError(err?.message || 'Generation failed. Check backend logs.');
    } finally {
      setIsRegenerating(false);
    }
  };

  const pdfUrl = `${BASE_URL}/generation/${docType === "cv" ? "cv" : "cover-letter"}/${companyId}?t=${timestamp}`;
  const label = docType === 'cv' ? 'Resume' : 'Cover Letter';

  const getScoreColor = (s) => {
    if (s >= 9.0) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/50";
    if (s >= 7.0) return "bg-amber-500/20 text-amber-400 border-amber-500/50";
    return "bg-red-500/20 text-red-400 border-red-500/50";
  };

  return (
    <div className="w-full h-full flex flex-col gap-3 relative group">

      {score != null && (
        <div className={`absolute -top-3 -right-3 px-3 py-1 bg-zinc-900 border rounded-full text-xs font-bold shadow-xl z-10 ${getScoreColor(score)}`}>
          {score.toFixed(1)}/10
        </div>
      )}

      <div className="relative w-full h-[300px] rounded-xl overflow-hidden shadow-2xl border border-zinc-700 bg-white">
        {isRegenerating ? (
          <div className="w-full h-full bg-zinc-900 flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-7 h-7 text-amber-400 animate-spin" />
            <p className="text-xs text-zinc-400 font-mono">Regenerating {label}…</p>
          </div>
        ) : regenError ? (
          <div className="w-full h-full bg-zinc-900 flex flex-col items-center justify-center gap-3 p-4">
            <AlertCircle className="w-7 h-7 text-red-400 flex-shrink-0" />
            <p className="text-xs text-red-400 font-semibold text-center">Generation failed</p>
            <p className="text-[10px] text-zinc-500 text-center leading-relaxed max-w-[220px]">
              {regenError}
            </p>
            {onRegenerate && (
              <button
                onClick={handleRegenerate}
                className="mt-1 flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 border
                           border-amber-500/30 text-amber-400 rounded-lg text-xs font-medium hover:bg-amber-500/20 transition-colors"
              >
                <RefreshCw className="w-3 h-3" /> Try Again
              </button>
            )}
          </div>
        ) : (
          <>
            <iframe
              key={`iframe-${timestamp}`}
              src={`${pdfUrl}#toolbar=0&navpanes=0&scrollbar=0`}
              className="w-full h-full pointer-events-none opacity-90 group-hover:opacity-100 transition-opacity duration-500"
              title={`${label} for ${companyId}`}
            />

            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3 backdrop-blur-sm">
              <button
                onClick={() => setIsFullscreen(true)}
                className="p-3 bg-[#6C63FF] hover:bg-[#5B54E6] text-white rounded-full transition-transform hover:scale-110 shadow-lg"
                title="View full screen"
              >
                <Maximize2 className="w-5 h-5" />
              </button>
              <a
                href={pdfUrl}
                download={`${docType}_${companyId}.pdf`}
                className="p-3 bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 text-white rounded-full transition-transform hover:scale-110 shadow-lg"
                title="Download PDF"
              >
                <FileDown className="w-5 h-5" />
              </a>
              {onRegenerate && (
                <button
                  onClick={handleRegenerate}
                  disabled={isRegenerating}
                  className="p-3 bg-amber-500/20 hover:bg-amber-500/40 border border-amber-500/40 text-amber-400
                             rounded-full transition-transform hover:scale-110 shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
                  title={`Regenerate ${label}`}
                >
                  <RefreshCw className="w-5 h-5" />
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {isFullscreen && (
        <div className="fixed inset-0 bg-black z-[100] flex flex-col">
          <div className="flex items-center justify-between px-5 py-3 bg-zinc-950 border-b border-zinc-800 flex-shrink-0">
            <span className="text-sm font-semibold text-white">{label}</span>
            <div className="flex items-center gap-3">
              {onRegenerate && (
                <button
                  onClick={handleRegenerate}
                  disabled={isRegenerating}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20
                             border border-amber-500/30 text-amber-400 rounded-lg text-xs font-medium
                             transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
                  {isRegenerating ? 'Regenerating…' : 'Regenerate'}
                </button>
              )}
              <a
                href={pdfUrl}
                download={`${docType}_${companyId}.pdf`}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700
                           text-zinc-300 rounded-lg text-xs font-medium transition-colors"
              >
                <FileDown className="w-3.5 h-3.5" /> Download
              </a>
              <button
                onClick={() => setIsFullscreen(false)}
                className="p-1.5 text-zinc-400 hover:text-white transition-colors rounded-lg hover:bg-zinc-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          <iframe
            src={pdfUrl}
            className="flex-1 w-full bg-zinc-800"
            title={`${label} full screen`}
          />
        </div>
      )}
    </div>
  );
};

export default CVPreview;
