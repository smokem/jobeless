import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { X, Save, Loader2, AlertCircle, Sparkles } from 'lucide-react';

const CVEditorModal = ({ companyId, docType = 'cv', onClose, onSaveSuccess }) => {
  const [jsonContent, setJsonContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchJson();
  }, [companyId]);

  const fetchJson = async () => {
    try {
      setLoading(true);
      const data = docType === 'cv' 
        ? await apiClient.getCVJson(companyId)
        : await apiClient.getCLJson(companyId);
      setJsonContent(JSON.stringify(data, null, 2));
    } catch (err) {
      setError("Failed to load document JSON.");
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async () => {
    try {
      setSaving(true);
      setError(null);
      const currentJson = JSON.parse(jsonContent);
      const optimized = await apiClient.optimizeCV(currentJson);
      setJsonContent(JSON.stringify(optimized, null, 2));
      
      // Auto-save after optimization to ensure re-render happens immediately
      if (docType === 'cv') {
        await apiClient.updateCVJson(companyId, optimized);
      } else {
        await apiClient.updateCLJson(companyId, optimized);
      }
      
      // Don't close modal yet, let them see the changes, but mark as success
      onSaveSuccess(false); // This updates the timestamp in the parent
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("Current editor content is invalid JSON. Fix it before optimizing.");
      } else {
        setError(err.message || "Optimization failed.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      const parsed = JSON.parse(jsonContent);
      
      if (docType === 'cv') {
        await apiClient.updateCVJson(companyId, parsed);
      } else {
        await apiClient.updateCLJson(companyId, parsed);
      }
      
      onSaveSuccess();
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("Invalid JSON format. Please check your syntax.");
      } else {
        setError(err.message || "Failed to save document.");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="bg-zinc-900 border border-zinc-800 w-full max-w-3xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-bottom border-zinc-800">
          <div>
            <h2 className="text-xl font-bold text-white uppercase tracking-tight">
              Edit {docType.toUpperCase()} Source
            </h2>
            <p className="text-xs text-zinc-500 mt-1">Directly edit the JSON to fix any unknowns or polish content.</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-full text-zinc-400 transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden p-6 pt-2">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center gap-4 text-zinc-500">
               <Loader2 className="w-8 h-8 animate-spin text-[#6C63FF]" />
               <span>Loading source data...</span>
            </div>
          ) : (
            <div className="h-full flex flex-col gap-4">
               {error && (
                 <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-lg text-sm flex items-center gap-3">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                 </div>
               )}
               <textarea
                 className="flex-1 w-full bg-zinc-950 text-zinc-300 font-mono text-sm p-4 rounded-xl border border-zinc-800 focus:ring-2 focus:ring-[#6C63FF] focus:border-transparent outline-none resize-none scrollbar-thin scrollbar-thumb-zinc-800"
                 spellCheck="false"
                 value={jsonContent}
                 onChange={(e) => setJsonContent(e.target.value)}
                 placeholder="Paste or edit CV JSON here..."
               />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-zinc-800 flex justify-between gap-4 bg-zinc-900/50">
           <button 
             onClick={handleOptimize}
             disabled={loading || saving}
             className="px-4 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-xl font-medium transition-all flex items-center gap-2"
           >
             {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
             AI Optimize (ATS)
           </button>

           <div className="flex gap-4">
              <button 
                onClick={onClose}
                className="px-4 py-2 text-zinc-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={handleSave}
                disabled={loading || saving}
                className="px-6 py-2 bg-[#6C63FF] hover:bg-[#5B54E6] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-bold transition-all shadow-lg flex items-center gap-2"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {saving ? "Rendering..." : "Save & Re-render"}
              </button>
           </div>
        </div>
      </div>
    </div>
  );
};

export default CVEditorModal;
