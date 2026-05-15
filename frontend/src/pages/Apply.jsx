import React, { useState, useEffect, useRef } from 'react';
import { apiClient, BASE_URL } from '../api/client';
import {
  Send, AlertTriangle, CheckCircle2, XCircle, Loader2,
  StopCircle, ExternalLink, FileText, RefreshCw, Shield,
  Star, Brain, Sparkles, X, BookOpen, Monitor, Clock
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import CVPreview from '../components/CVPreview';

const INSIGHT_LABELS = {
  what_they_look_for: 'What They Look For',
  red_flag: 'Red Flag to Avoid',
  cultural_keyword: 'Cultural Keyword',
  communication_style: 'Communication Style',
  tone: 'Tone Preference',
};

const Apply = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [autoTargets, setAutoTargets] = useState([]);
  const [manualTargets, setManualTargets] = useState([]);
  const [metaData, setMetaData] = useState({});
  const [loading, setLoading] = useState(true);

  const [isRunning, setIsRunning] = useState(false);
  const [progressLog, setProgressLog] = useState([]);
  const [countdown, setCountdown] = useState(null); // seconds remaining in inter-app wait
  const esRef = useRef(null);

  // Insight explanation modal state
  const [selectedInsight, setSelectedInsight] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [explainLoading, setExplainLoading] = useState(false);

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [stats, allTargets] = await Promise.all([
        apiClient.getApplyStatus(),
        apiClient.getTargets(),
      ]);
      setStatus(stats);
      const pending = allTargets.filter(t => t.status === 'pending');
      const auto = pending.filter(t => t.apply_type !== 'external');
      const manual = pending.filter(t => t.apply_type === 'external');
      setAutoTargets(auto);
      setManualTargets(manual);

      const results = {};
      await Promise.all(manual.map(async (t) => {
        try {
          const [meta, iters] = await Promise.all([
            apiClient.getApplicationMeta(t.company_id),
            apiClient.getGANIterations(t.company_id),
          ]);
          const score = iters?.length > 0 ? iters[iters.length - 1].score : null;
          results[t.company_id] = { persona: meta?.persona, score };
        } catch (_) {}
      }));
      setMetaData(results);
    } catch (err) {
      console.error('Failed to load apply status', err);
    } finally {
      setLoading(false);
    }
  };

  const upsertLog = (companyId, name, logStatus, extra = {}) => {
    setProgressLog(prev => {
      const idx = prev.findIndex(p => p.company_id === companyId);
      const entry = { company_id: companyId, name, status: logStatus, ...extra };
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = entry;
        return next;
      }
      return [entry, ...prev];
    });
  };

  const handleStartQueue = () => {
    if (autoTargets.length === 0 || isRunning) return;
    setIsRunning(true);
    setProgressLog([]);
    setCountdown(null);

    const es = new EventSource(`${BASE_URL}/apply/batch/stream`);
    esRef.current = es;

    es.onmessage = (e) => {
      const data = e.data;

      if (data.startsWith('PREPARING|')) {
        const [, id, name] = data.split('|');
        setCountdown(null);
        upsertLog(id, name, 'processing');
        return;
      }

      if (data.startsWith('DONE_ONE|')) {
        const [, id, name, outcome] = data.split('|');
        upsertLog(id, name, outcome === 'success' ? 'success' : 'failed');
        return;
      }

      if (data.startsWith('ERROR_ONE|')) {
        const [, id, name, ...rest] = data.split('|');
        upsertLog(id, name, 'error', { error: rest.join('|') });
        return;
      }

      if (data.startsWith('WAITING|')) {
        const secs = parseInt(data.split('|')[1], 10);
        setCountdown(secs);
        return;
      }

      if (data.startsWith('TICK|')) {
        const secs = parseInt(data.split('|')[1], 10);
        setCountdown(secs);
        return;
      }

      if (data.startsWith('LIMIT_REACHED|')) {
        const max = data.split('|')[1];
        setProgressLog(prev => [
          { company_id: '__limit__', name: `Daily limit of ${max} reached`, status: 'limit' },
          ...prev,
        ]);
        finish();
        return;
      }

      if (data === 'BATCH_DONE') {
        finish();
      }
    };

    es.onerror = () => {
      setProgressLog(prev => [
        { company_id: '__err__', name: 'Connection lost', status: 'error', error: 'SSE connection dropped' },
        ...prev,
      ]);
      finish();
    };
  };

  const finish = () => {
    esRef.current?.close();
    esRef.current = null;
    setIsRunning(false);
    setCountdown(null);
    fetchData();
  };

  const handleAbort = () => {
    esRef.current?.close();
    esRef.current = null;
    setIsRunning(false);
    setCountdown(null);
    setProgressLog(prev => [
      { company_id: '__abort__', name: 'Queue aborted by user', status: 'aborted' },
      ...prev,
    ]);
    fetchData();
  };

  const handleRegenerateDoc = (company_id, doc_type) => {
    const trigger = doc_type === 'cv'
      ? apiClient.generateCV(company_id)
      : apiClient.generateCoverLetter(company_id);

    return trigger.then(() => new Promise((resolve, reject) => {
      const es = new EventSource(`${BASE_URL}/generation/status/${company_id}`);
      es.onmessage = (e) => {
        if (e.data.startsWith('DONE|')) {
          if (doc_type === 'cv') {
            const score = parseFloat(e.data.split('|')[1]);
            setMetaData(prev => ({
              ...prev,
              [company_id]: { ...prev[company_id], score },
            }));
          }
          es.close(); resolve();
        } else if (e.data.startsWith('ERROR|')) {
          es.close(); reject(new Error(e.data.replace('ERROR|', '')));
        }
      };
      es.onerror = () => { es.close(); reject(new Error('SSE connection failed')); };
    }));
  };

  const handleInsightClick = async (companyId, type, value) => {
    if (explainLoading) return;
    setSelectedInsight({ companyId, type, value });
    setExplanation(null);
    setExplainLoading(true);
    try {
      const result = await apiClient.explainInsight(companyId, type, value);
      setExplanation(result);
    } catch {
      setExplanation({ error: true });
    } finally {
      setExplainLoading(false);
    }
  };

  const closeModal = () => {
    setSelectedInsight(null);
    setExplanation(null);
    setExplainLoading(false);
  };

  const logStatusStyle = (s) => {
    if (s === 'processing') return 'bg-[#6C63FF]/10 border-[#6C63FF]/30';
    if (s === 'success')    return 'bg-emerald-500/10 border-emerald-500/30';
    if (s === 'failed' || s === 'error') return 'bg-red-500/10 border-red-500/30';
    if (s === 'limit')      return 'bg-amber-500/10 border-amber-500/30';
    return 'bg-zinc-900/50 border-zinc-800';
  };

  if (loading) return (
    <div className="p-8 flex justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-[#6C63FF]" />
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-12">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Apply</h1>
        <p className="text-zinc-500 text-sm mt-1">Submit your prepared applications.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-zinc-400 mb-1">Auto Queue</h3>
          <p className="text-3xl font-bold text-white">{autoTargets.length}</p>
          <p className="text-xs text-zinc-600 mt-1">LinkedIn Easy Apply + Email</p>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-zinc-400 mb-1">Sent Today</h3>
          <p className="text-3xl font-bold text-emerald-400">
            {status?.sent_today} <span className="text-sm text-zinc-500">/ {status?.max_limit}</span>
          </p>
        </div>
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-zinc-400 mb-1">Remaining</h3>
          <p className="text-3xl font-bold text-[#6C63FF]">{status?.remaining_today}</p>
        </div>
      </div>

      {status?.remaining_today < autoTargets.length && autoTargets.length > 0 && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-amber-200">
            Your queue ({autoTargets.length}) exceeds your remaining daily limit ({status.remaining_today}).
            The queue will stop once the limit is reached.
          </p>
        </div>
      )}

      {/* ── Auto-apply execution panel ── */}
      {autoTargets.length > 0 && (
        <div className="bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white">Automated Queue</h2>
            <div className="flex gap-3">
              {!isRunning && (
                <button
                  onClick={handleStartQueue}
                  disabled={autoTargets.length === 0 || status?.remaining_today <= 0}
                  className="px-6 py-2 bg-[#6C63FF] hover:bg-[#5B54E6] disabled:opacity-50 disabled:cursor-not-allowed
                             text-white rounded-lg font-bold transition flex items-center gap-2"
                >
                  <Send className="w-4 h-4" /> Start Apply Queue
                </button>
              )}
              {isRunning && (
                <button
                  onClick={handleAbort}
                  className="px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-bold transition
                             flex items-center gap-2 shadow-lg shadow-red-500/20"
                >
                  <StopCircle className="w-4 h-4" /> Abort
                </button>
              )}
            </div>
          </div>

          {/* Browser-active banner */}
          {isRunning && (
            <div className="mb-4 flex items-center gap-3 px-4 py-3 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
              <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
              </span>
              <Monitor className="w-4 h-4 text-emerald-400" />
              <span className="text-sm text-emerald-300 font-medium">
                Browser window is live — you can see and intervene at any time
              </span>
              {countdown !== null && (
                <div className="ml-auto flex items-center gap-1.5 text-zinc-400 text-sm">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Next in <span className="font-mono text-white">{countdown}s</span></span>
                </div>
              )}
            </div>
          )}

          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
            {progressLog.length === 0 && (
              <div className="text-center py-10 text-zinc-600 font-mono text-sm border border-zinc-800 border-dashed rounded-xl">
                Awaiting execution…
              </div>
            )}
            {progressLog.map((log, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-xl border flex items-center justify-between ${logStatusStyle(log.status)}`}
              >
                <div className="flex items-center gap-3">
                  {log.status === 'processing' && <Loader2 className="w-5 h-5 text-[#6C63FF] animate-spin" />}
                  {log.status === 'success'    && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                  {(log.status === 'error' || log.status === 'failed') && <XCircle className="w-5 h-5 text-red-400" />}
                  {log.status === 'aborted'    && <StopCircle className="w-5 h-5 text-zinc-400" />}
                  {log.status === 'limit'      && <AlertTriangle className="w-5 h-5 text-amber-400" />}
                  <div>
                    <h4 className="text-white font-medium">{log.name}</h4>
                    {log.error && <p className="text-xs text-red-400 mt-1">{log.error}</p>}
                  </div>
                </div>
                <span className="text-xs font-mono uppercase tracking-widest text-zinc-500">{log.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Manual applications ── */}
      {manualTargets.length > 0 && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Manual Applications</h2>
                <p className="text-sm text-zinc-500">
                  Apply on the company site — your tailored documents and persona context are below.
                </p>
              </div>
            </div>
            <span className="text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-1 rounded">
              {manualTargets.length} pending
            </span>
          </div>

          {manualTargets.map(target => {
            const data = metaData[target.company_id] || {};
            const persona = data.persona;
            const score = data.score;
            const hasDocs = score != null;

            const Chip = ({ type, value, colorClass }) => (
              <button
                onClick={() => handleInsightClick(target.company_id, type, value)}
                title="Click to understand why"
                className={`text-[11px] px-2 py-0.5 rounded-full border transition-all cursor-pointer
                            hover:scale-105 active:scale-95 ${colorClass}`}
              >
                {value}
              </button>
            );

            return (
              <div key={target.company_id} className="bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/40">
                  <div>
                    <h3 className="text-lg font-bold text-white">{target.company_name}</h3>
                    <p className="text-sm text-zinc-400">{target.job_title} · {target.location}</p>
                  </div>
                  <a
                    href={target.job_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600
                               text-black font-bold rounded-xl text-sm transition-colors shadow-lg shadow-amber-500/20"
                  >
                    Apply Now <ExternalLink className="w-4 h-4" />
                  </a>
                </div>

                {/* Body: Persona left | Documents right */}
                <div className="flex flex-col lg:flex-row">

                  {/* Left: Persona context */}
                  <div className="flex-1 p-5 border-b lg:border-b-0 lg:border-r border-zinc-800 space-y-4">
                    <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-semibold">
                      HR Context
                      {persona && (
                        <span className="ml-2 normal-case font-normal text-zinc-700">— click any chip to see why</span>
                      )}
                    </p>

                    {persona ? (
                      <>
                        {persona.what_they_look_for?.length > 0 && (
                          <div>
                            <p className="text-xs text-zinc-500 mb-2 flex items-center gap-1">
                              <Star className="w-3 h-3" /> What they look for
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {persona.what_they_look_for.map((v, i) => (
                                <Chip key={i} type="what_they_look_for" value={v}
                                  colorClass="bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/25 hover:border-emerald-500/50" />
                              ))}
                            </div>
                          </div>
                        )}

                        {persona.red_flags_to_avoid?.length > 0 && (
                          <div>
                            <p className="text-xs text-zinc-500 mb-2 flex items-center gap-1">
                              <Shield className="w-3 h-3" /> Red flags to avoid
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {persona.red_flags_to_avoid.map((v, i) => (
                                <Chip key={i} type="red_flag" value={v}
                                  colorClass="bg-red-500/10 border-red-500/20 text-red-400 hover:bg-red-500/25 hover:border-red-500/50" />
                              ))}
                            </div>
                          </div>
                        )}

                        {persona.cultural_keywords?.length > 0 && (
                          <div>
                            <p className="text-xs text-zinc-500 mb-2">Keywords to mirror</p>
                            <div className="flex flex-wrap gap-1.5">
                              {persona.cultural_keywords.map((k, i) => (
                                <Chip key={i} type="cultural_keyword" value={k}
                                  colorClass="bg-amber-500/10 border-amber-500/20 text-amber-400 hover:bg-amber-500/25 hover:border-amber-500/50" />
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          {persona.tone_preference && (
                            <>
                              <span className="text-xs text-zinc-500">Tone:</span>
                              <Chip type="tone" value={persona.tone_preference}
                                colorClass="bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:border-zinc-600 capitalize" />
                            </>
                          )}
                          {persona.hr_communication_style && (
                            <button
                              onClick={() => handleInsightClick(target.company_id, 'communication_style', persona.hr_communication_style)}
                              title="Click to understand why"
                              className="text-xs text-zinc-500 italic hover:text-zinc-300 transition-colors"
                            >
                              — {persona.hr_communication_style}
                            </button>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="py-8 flex flex-col items-center gap-3 border border-dashed border-zinc-800 rounded-xl text-zinc-600">
                        <Brain className="w-6 h-6 opacity-40" />
                        <p className="text-xs text-center leading-relaxed">
                          No persona built yet.<br />Generate documents in Review first.
                        </p>
                        <button
                          onClick={() => navigate('/review')}
                          className="text-xs text-[#6C63FF] hover:underline"
                        >
                          Go to Review →
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Right: Document previews */}
                  <div className="lg:w-[520px] p-5 bg-zinc-900/20">
                    <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-semibold mb-4">
                      Your Documents
                    </p>

                    {hasDocs ? (
                      <div className="flex gap-4">
                        <div className="flex-1 flex flex-col">
                          <span className="text-[10px] text-zinc-500 font-bold uppercase mb-2">Resume</span>
                          <CVPreview
                            companyId={target.company_id}
                            score={score}
                            docType="cv"
                            onRegenerate={() => handleRegenerateDoc(target.company_id, 'cv')}
                          />
                        </div>
                        <div className="flex-1 flex flex-col">
                          <span className="text-[10px] text-zinc-500 font-bold uppercase mb-2">Cover Letter</span>
                          <CVPreview
                            companyId={target.company_id}
                            docType="cover_letter"
                            onRegenerate={() => handleRegenerateDoc(target.company_id, 'cover_letter')}
                          />
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center gap-3 min-h-[260px]
                                      border-2 border-dashed border-zinc-800 rounded-xl text-zinc-600">
                        <FileText className="w-8 h-8 opacity-40" />
                        <p className="text-xs uppercase font-mono tracking-widest opacity-60">No Documents Yet</p>
                        <button
                          onClick={() => navigate('/review')}
                          className="px-4 py-2 bg-[#6C63FF]/10 border border-[#6C63FF]/30 text-[#6C63FF]
                                     rounded-lg text-sm font-medium hover:bg-[#6C63FF]/20 transition-colors"
                        >
                          Generate in Review →
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty state */}
      {autoTargets.length === 0 && manualTargets.length === 0 && (
        <div className="text-center py-16 text-zinc-600 border-2 border-dashed border-zinc-800 rounded-2xl">
          <Send className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm font-mono uppercase tracking-widest opacity-50">No targets in queue</p>
          <button
            onClick={() => navigate('/discover')}
            className="mt-4 text-sm text-[#6C63FF] hover:underline"
          >
            Go to Discovery to add jobs →
          </button>
        </div>
      )}

      {!isRunning && progressLog.length > 0 && (
        <div className="flex justify-end gap-3">
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl font-medium transition flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-white hover:bg-zinc-200 text-black rounded-xl font-bold transition"
          >
            Return to Dashboard
          </button>
        </div>
      )}

      {/* ── Insight Explanation Modal ── */}
      {selectedInsight && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={closeModal}
        >
          <div
            className="bg-zinc-950 border border-zinc-700 rounded-2xl w-full max-w-lg shadow-2xl shadow-black/60"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-start justify-between px-5 py-4 border-b border-zinc-800">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#6C63FF]/10 border border-[#6C63FF]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4 text-[#6C63FF]" />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-zinc-500">
                    {INSIGHT_LABELS[selectedInsight.type] || selectedInsight.type}
                  </p>
                  <p className="font-bold text-white text-sm mt-0.5 leading-snug">
                    {selectedInsight.value}
                  </p>
                </div>
              </div>
              <button onClick={closeModal} className="text-zinc-600 hover:text-white transition-colors ml-4 flex-shrink-0 p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
              {explainLoading && (
                <div className="flex items-center gap-3 py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-[#6C63FF]" />
                  <span className="text-sm text-zinc-400">Analyzing source data…</span>
                </div>
              )}

              {explanation && !explanation.error && (
                <>
                  {explanation.term_definition && (
                    <div className="flex gap-3 p-3 bg-zinc-900/80 border border-zinc-800 rounded-xl">
                      <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <BookOpen className="w-3.5 h-3.5 text-amber-400" />
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-widest text-amber-500/70 font-semibold mb-1">
                          What this term means
                        </p>
                        <p className="text-sm text-zinc-300 leading-relaxed">{explanation.term_definition}</p>
                      </div>
                    </div>
                  )}

                  {explanation.source_quote && (
                    <div className="bg-zinc-900 border-l-2 border-[#6C63FF] pl-3 py-2.5 rounded-r-lg">
                      <p className="text-[10px] uppercase tracking-widest text-zinc-600 mb-1.5">From the job posting</p>
                      <p className="text-xs text-zinc-400 italic leading-relaxed">"{explanation.source_quote}"</p>
                    </div>
                  )}

                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-semibold mb-2">
                      Why the AI flagged this
                    </p>
                    <p className="text-sm text-zinc-300 leading-relaxed">{explanation.why_identified}</p>
                  </div>

                  <div className="p-3 bg-[#6C63FF]/5 border border-[#6C63FF]/20 rounded-xl">
                    <p className="text-[10px] uppercase tracking-widest text-[#6C63FF]/70 font-semibold mb-1.5">
                      What to do about it
                    </p>
                    <p className="text-sm text-zinc-300 leading-relaxed">{explanation.what_it_means}</p>
                  </div>

                  {explanation.priority && (
                    <div className="flex items-center gap-2 pt-1 border-t border-zinc-800/60">
                      <span className="text-[10px] text-zinc-600">Priority:</span>
                      <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${
                        explanation.priority === 'high'
                          ? 'bg-red-500/15 text-red-400 border-red-500/30'
                          : explanation.priority === 'medium'
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                      }`}>
                        {explanation.priority}
                      </span>
                    </div>
                  )}
                </>
              )}

              {explanation?.error && (
                <p className="text-sm text-red-400">Could not load explanation. Try again.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Apply;
