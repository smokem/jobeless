import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import {
  Zap, MapPin, Target, Search, Check, CheckCircle2, ChevronRight,
  PlusCircle, X, ExternalLink, Trash2, User, Briefcase
} from 'lucide-react';

// ── Manual Add Modal ────────────────────────────────────────────────────────

const EMPTY_FORM = {
  company_name: '', job_title: '', job_url: '', location: '',
  apply_type: 'external', company_linkedin: '', company_website: '',
  hr_name: '', hr_linkedin: '', ceo_name: '', ceo_linkedin: '',
};

const ManualAddModal = ({ onClose, onAdded }) => {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.company_name || !form.job_title || !form.job_url || !form.location) {
      setError('Company name, job title, URL and location are required.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const target = await apiClient.addManualTarget(form);
      onAdded(target);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const Field = ({ label, k, placeholder, required = false, type = 'text' }) => (
    <div>
      <label className="block text-xs font-medium text-zinc-400 mb-1.5">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      <input
        type={type}
        value={form[k]}
        onChange={e => set(k, e.target.value)}
        placeholder={placeholder}
        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white
                   placeholder-zinc-600 focus:outline-none focus:border-[#6C63FF] focus:ring-1 focus:ring-[#6C63FF]"
      />
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#6C63FF]/10 border border-[#6C63FF]/20 flex items-center justify-center">
              <PlusCircle className="w-5 h-5 text-[#6C63FF]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Add Job Manually</h2>
              <p className="text-xs text-zinc-500">Paste a listing you found yourself</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
            <X className="w-5 h-5 text-zinc-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          {/* Core fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Company Name" k="company_name" placeholder="Acme Corp" required />
            <Field label="Job Title" k="job_title" placeholder="Senior Frontend Developer" required />
          </div>
          <Field label="Job Posting URL" k="job_url" placeholder="https://linkedin.com/jobs/view/…" required />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Location" k="location" placeholder="Remote / Paris, France" required />
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">Apply Type</label>
              <select
                value={form.apply_type}
                onChange={e => set('apply_type', e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white
                           focus:outline-none focus:border-[#6C63FF] focus:ring-1 focus:ring-[#6C63FF]"
              >
                <option value="easy_apply">LinkedIn Easy Apply</option>
                <option value="external">External (redirect)</option>
                <option value="email">Email Application</option>
              </select>
            </div>
          </div>

          {/* Optional company info */}
          <div className="border-t border-zinc-800 pt-4">
            <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold mb-3">
              Optional — improves persona research
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Company LinkedIn URL" k="company_linkedin" placeholder="linkedin.com/company/acme" />
              <Field label="Company Website" k="company_website" placeholder="https://acme.com" />
            </div>
          </div>

          {/* HR / CEO */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="HR Contact Name" k="hr_name" placeholder="Jane Smith" />
            <Field label="HR LinkedIn URL" k="hr_linkedin" placeholder="linkedin.com/in/jane" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="CEO / Founder Name" k="ceo_name" placeholder="John Doe" />
            <Field label="CEO LinkedIn URL" k="ceo_linkedin" placeholder="linkedin.com/in/john" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="px-5 py-2 bg-[#6C63FF] hover:bg-[#5B54E6] text-white rounded-lg text-sm font-semibold
                         transition-colors disabled:opacity-50 flex items-center gap-2">
              {saving ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : <PlusCircle className="w-4 h-4" />}
              {saving ? 'Adding…' : 'Add to Targets'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Main Discovery Page ─────────────────────────────────────────────────────

const Discovery = () => {
  const navigate = useNavigate();

  const [loadingRoles, setLoadingRoles] = useState(false);
  const [roleSuggestions, setRoleSuggestions] = useState([]);
  const [selectedRole, setSelectedRole] = useState('');
  const [location, setLocation] = useState('');
  const [radius, setRadius] = useState(25);
  const [isScraping, setIsScraping] = useState(false);
  const [targets, setTargets] = useState([]);
  const [selectedTargets, setSelectedTargets] = useState(new Set());
  const [scrapeError, setScrapeError] = useState(null);
  const [showManualModal, setShowManualModal] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    apiClient.getTargets()
      .then(existing => {
        if (existing?.length) {
          setTargets(existing);
          setSelectedTargets(new Set(existing.filter(t => t.status !== 'ignored').map(t => t.company_id)));
        }
      })
      .catch(() => {});
  }, []);

  const handleSuggestRoles = async () => {
    setLoadingRoles(true);
    setScrapeError(null);
    try {
      const suggestions = await apiClient.suggestRoles();
      setRoleSuggestions(suggestions);
      if (suggestions.length > 0) setSelectedRole(suggestions[0].role);
    } catch {
      setScrapeError('Failed to fetch role suggestions. Ensure backend and OpenRouter API key are configured.');
    } finally {
      setLoadingRoles(false);
    }
  };

  const handleScrape = async () => {
    if (!selectedRole || !location) {
      setScrapeError('Please enter a target role and location before searching.');
      return;
    }
    setIsScraping(true);
    setScrapeError(null);
    try {
      const result = await apiClient.scrapeJobs({ role: selectedRole, location, radius_km: radius });
      const preview = result.preview || [];
      setTargets(preview);
      setSelectedTargets(new Set(preview.map(t => t.company_id)));
    } catch (err) {
      setScrapeError('Failed to scrape jobs: ' + err.message);
    } finally {
      setIsScraping(false);
    }
  };

  const handleManualAdded = (target) => {
    setTargets(prev => [...prev, target]);
    setSelectedTargets(prev => new Set([...prev, target.company_id]));
  };

  const toggleTarget = (id) => {
    setSelectedTargets(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleDelete = async (companyId) => {
    setDeletingId(companyId);
    try {
      await apiClient.deleteTarget(companyId);
      setTargets(prev => prev.filter(t => t.company_id !== companyId));
      setSelectedTargets(prev => { const n = new Set(prev); n.delete(companyId); return n; });
    } catch (err) {
      setScrapeError('Failed to delete target: ' + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleFinalize = async () => {
    try {
      await apiClient.finalizeTargets(Array.from(selectedTargets));
      navigate('/review');
    } catch {
      setScrapeError('Failed to finalize targets.');
    }
  };

  // Safe URL opener — ensures absolute URL
  const safeJobUrl = (url) => {
    if (!url) return null;
    try { return new URL(url).href; } catch { return null; }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-12">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Job Discovery</h1>
        <p className="text-zinc-500 text-sm mt-1">Find target roles via AI + scraping, or add listings manually.</p>
      </div>

      {scrapeError && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm">
          {scrapeError}
        </div>
      )}

      {/* ── Section 1: Role ── */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#6C63FF]/10 flex items-center justify-center border border-[#6C63FF]/20">
              <Zap className="w-5 h-5 text-[#6C63FF]" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Target Role</h2>
              <p className="text-zinc-500 text-sm">What position are you applying for?</p>
            </div>
          </div>
          <button
            onClick={handleSuggestRoles}
            disabled={loadingRoles}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-medium
                       transition-colors border border-zinc-700 flex items-center gap-2"
          >
            {loadingRoles
              ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              : <SparklesIcon />}
            {loadingRoles ? 'Analyzing…' : 'AI Suggest Roles'}
          </button>
        </div>

        {roleSuggestions.length > 0 ? (
          <div className="grid gap-3">
            {roleSuggestions.map((sug, idx) => (
              <label
                key={idx}
                className={`relative flex items-start gap-4 p-4 rounded-xl border cursor-pointer transition-all ${
                  selectedRole === sug.role
                    ? 'bg-[#6C63FF]/5 border-[#6C63FF]/30 ring-1 ring-[#6C63FF]/50'
                    : 'bg-zinc-900/50 border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center h-5">
                  <input
                    type="radio" name="role" value={sug.role}
                    checked={selectedRole === sug.role}
                    onChange={e => setSelectedRole(e.target.value)}
                    className="w-4 h-4 text-[#6C63FF] bg-zinc-800 border-zinc-700"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-4 mb-1">
                    <span className="font-semibold text-white">{sug.role}</span>
                    <span className="text-xs font-mono font-medium text-emerald-400">
                      {Math.round((sug.match_score || 0) * 100)}% Match
                    </span>
                  </div>
                  <p className="text-sm text-zinc-400">{sug.reasoning}</p>
                </div>
              </label>
            ))}
            <div className="flex items-center gap-4 mt-2">
              <span className="text-sm text-zinc-500 whitespace-nowrap">Or enter manually:</span>
              <input
                type="text" placeholder="e.g. Frontend Developer" value={selectedRole}
                onChange={e => { setSelectedRole(e.target.value); setRoleSuggestions([]); }}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-white
                           focus:outline-none focus:border-[#6C63FF]"
              />
            </div>
          </div>
        ) : (
          <input
            type="text" placeholder="e.g. Frontend Developer" value={selectedRole}
            onChange={e => setSelectedRole(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white
                       focus:outline-none focus:border-[#6C63FF]"
          />
        )}
      </div>

      {/* ── Section 2: Location & Search ── */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
            <MapPin className="w-5 h-5 text-amber-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Location Target</h2>
            <p className="text-zinc-500 text-sm">Where are you looking to work?</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">City, Country or Remote</label>
            <input
              type="text" placeholder="e.g. Paris, France or Remote" value={location}
              onChange={e => setLocation(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white
                         focus:outline-none focus:border-[#6C63FF]"
            />
          </div>
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-zinc-400">Search Radius</label>
              <span className="text-sm font-mono text-zinc-300">+{radius} km</span>
            </div>
            <input
              type="range" min="10" max="150" step="10" value={radius}
              onChange={e => setRadius(parseInt(e.target.value))}
              className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-[#6C63FF]"
            />
            <div className="flex justify-between text-xs text-zinc-500 mt-2 font-mono">
              <span>10km</span><span>150km</span>
            </div>
          </div>
        </div>

        <button
          onClick={handleScrape}
          disabled={isScraping}
          className="w-full py-3.5 bg-[#6C63FF] hover:bg-[#5B54E6] text-white rounded-xl font-semibold
                     transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isScraping
            ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            : <Search className="w-5 h-5" />}
          {isScraping ? 'Searching LinkedIn…' : 'Find Companies'}
        </button>
      </div>

      {/* ── Section 3: Target List ── */}
      {(targets.length > 0 || true) && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                <Target className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Target Validation</h2>
                <p className="text-zinc-500 text-sm">
                  {targets.length > 0
                    ? `${targets.length} listing${targets.length !== 1 ? 's' : ''}. Review and confirm.`
                    : 'Add listings manually or scrape above.'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {targets.length > 0 && (
                <span className="text-sm">
                  <span className="text-emerald-400 font-bold">{selectedTargets.size}</span>
                  <span className="text-zinc-500"> / {targets.length} selected</span>
                </span>
              )}
              <button
                onClick={() => setShowManualModal(true)}
                className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white
                           rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
              >
                <PlusCircle className="w-4 h-4 text-[#6C63FF]" />
                Add Manually
              </button>
            </div>
          </div>

          {targets.length > 0 ? (
            <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
              {targets.map((target, idx) => {
                const isSelected = selectedTargets.has(target.company_id);
                const jobUrl = safeJobUrl(target.job_url);
                return (
                  <div
                    key={target.company_id || idx}
                    className={`flex items-start justify-between p-4 rounded-xl border transition-colors ${
                      isSelected ? 'bg-zinc-800/50 border-zinc-700' : 'bg-zinc-900/50 border-zinc-800/50 opacity-55'
                    }`}
                  >
                    <div className="flex items-start gap-4 flex-1 min-w-0">
                      <button
                        onClick={() => toggleTarget(target.company_id)}
                        className={`flex-shrink-0 mt-0.5 w-6 h-6 rounded flex items-center justify-center border transition-colors ${
                          isSelected ? 'bg-emerald-500 border-emerald-500 text-white' : 'bg-zinc-800 border-zinc-600'
                        }`}
                      >
                        {isSelected && <Check className="w-4 h-4" />}
                      </button>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className={`font-semibold text-white ${!isSelected ? 'line-through text-zinc-500' : ''}`}>
                            {target.company_name}
                          </h3>
                          {target.company_id.startsWith('manual_') && (
                            <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded">
                              manual
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="text-xs text-zinc-400 flex items-center gap-1">
                            <Briefcase className="w-3 h-3" />{target.job_title}
                          </span>
                          <span className="text-zinc-600">•</span>
                          <span className="text-xs text-zinc-400 flex items-center gap-1">
                            <MapPin className="w-3 h-3" />{target.location}
                          </span>
                        </div>

                        {/* HR / CEO info if available */}
                        {(target.hr_name || target.ceo_name) && (
                          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                            {target.hr_name && (
                              <span className="text-[11px] text-zinc-500 flex items-center gap-1">
                                <User className="w-3 h-3 text-blue-400" />
                                HR: <span className="text-zinc-400">{target.hr_name}</span>
                              </span>
                            )}
                            {target.ceo_name && (
                              <span className="text-[11px] text-zinc-500 flex items-center gap-1">
                                <User className="w-3 h-3 text-purple-400" />
                                CEO: <span className="text-zinc-400">{target.ceo_name}</span>
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-2 ml-3 flex-shrink-0">
                      <span className="text-[10px] font-mono tracking-wider uppercase px-2 py-1 bg-zinc-800 rounded text-zinc-400">
                        {target.apply_type.replace('_', ' ')}
                      </span>
                      <div className="flex items-center gap-2">
                        {jobUrl ? (
                          <a
                            href={jobUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-[#6C63FF] hover:text-[#8B85FF] flex items-center gap-1 transition-colors"
                            title={jobUrl}
                          >
                            View Post <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : (
                          <span className="text-xs text-zinc-600">No URL</span>
                        )}
                        <button
                          onClick={() => handleDelete(target.company_id)}
                          disabled={deletingId === target.company_id}
                          className="p-1 hover:bg-zinc-700 rounded text-zinc-600 hover:text-red-400 transition-colors"
                          title="Remove target"
                        >
                          {deletingId === target.company_id
                            ? <div className="w-3.5 h-3.5 border border-zinc-500 border-t-transparent rounded-full animate-spin" />
                            : <Trash2 className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-10 text-zinc-600 border-2 border-dashed border-zinc-800 rounded-xl">
              <PlusCircle className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No listings yet. Scrape LinkedIn above or add one manually.</p>
            </div>
          )}

          {targets.length > 0 && (
            <div className="pt-2 flex justify-end">
              <button
                onClick={handleFinalize}
                disabled={selectedTargets.size === 0}
                className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-semibold
                           transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <CheckCircle2 className="w-5 h-5" />
                Approve & Proceed
                <ChevronRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          )}
        </div>
      )}

      {showManualModal && (
        <ManualAddModal
          onClose={() => setShowManualModal(false)}
          onAdded={handleManualAdded}
        />
      )}
    </div>
  );
};

const SparklesIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
    <path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>
  </svg>
);

export default Discovery;
