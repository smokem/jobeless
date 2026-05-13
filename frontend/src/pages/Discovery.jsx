import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Zap, MapPin, Target, Search, Building2, CheckCircle2, ChevronRight, Check } from 'lucide-react';

const Discovery = () => {
  const navigate = useNavigate();
  // Role selection state
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [roleSuggestions, setRoleSuggestions] = useState([]);
  const [selectedRole, setSelectedRole] = useState("");

  // Search params state
  const [location, setLocation] = useState("");
  const [radius, setRadius] = useState(25);

  // Scraping state
  const [isScraping, setIsScraping] = useState(false);
  const [targets, setTargets] = useState([]);
  const [scrapeError, setScrapeError] = useState(null);

  // Toggle tracking
  const [selectedTargets, setSelectedTargets] = useState(new Set());

  // Check if there are already targets
  useEffect(() => {
    const fetchExistingTargets = async () => {
      try {
        const existing = await apiClient.getTargets();
        if (existing && existing.length > 0) {
          setTargets(existing);
          setSelectedTargets(new Set(existing.map(t => t.company_id)));
        }
      } catch (err) {
        console.log("No existing targets found.");
      }
    };
    fetchExistingTargets();
  }, []);

  const handleSuggestRoles = async () => {
    setLoadingRoles(true);
    setScrapeError(null);
    try {
      const suggestions = await apiClient.suggestRoles();
      setRoleSuggestions(suggestions);
      if (suggestions.length > 0) {
        setSelectedRole(suggestions[0].role);
      }
    } catch (err) {
      setScrapeError("Failed to fetch role suggestions. Ensure Backend and Groq API are configured.");
    } finally {
      setLoadingRoles(false);
    }
  };

  const handleScrape = async () => {
    if (!selectedRole || !location) return;
    
    setIsScraping(true);
    setScrapeError(null);
    try {
      const result = await apiClient.scrapeJobs({
        role: selectedRole,
        location,
        radius_km: radius
      });
      setTargets(result.preview || []);
      setSelectedTargets(new Set(result.preview.map(t => t.company_id)));
    } catch (err) {
      setScrapeError("Failed to scrape jobs: " + err.message);
    } finally {
      setIsScraping(false);
    }
  };

  const toggleTarget = (id) => {
    const newSelected = new Set(selectedTargets);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedTargets(newSelected);
  };

  const handleFinalize = async () => {
    try {
      await apiClient.finalizeTargets(Array.from(selectedTargets));
      navigate('/review'); // Proceed to next phase
    } catch (err) {
      setScrapeError("Failed to finalize targets.");
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-12">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Job Discovery</h1>
        <p className="text-zinc-500 text-sm mt-1">Let AI find the perfect roles for your profile.</p>
      </div>

      {scrapeError && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm">
          {scrapeError}
        </div>
      )}

      {/* Section 1: Role Selection */}
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
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors border border-zinc-700 flex items-center gap-2"
          >
            {loadingRoles ? (
               <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : <SparklesIcon />}
            {loadingRoles ? 'Analyzing Profile...' : 'AI Suggest Roles'}
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
                    type="radio" 
                    name="role" 
                    value={sug.role}
                    checked={selectedRole === sug.role}
                    onChange={(e) => setSelectedRole(e.target.value)}
                    className="w-4 h-4 text-[#6C63FF] bg-zinc-800 border-zinc-700 focus:ring-[#6C63FF] focus:ring-offset-zinc-900" 
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-4 mb-1">
                    <span className="font-semibold text-white">{sug.role}</span>
                    <span className="text-xs font-mono font-medium text-emerald-400">
                      {Math.round(sug.match_score * 100)}% Match
                    </span>
                  </div>
                  <p className="text-sm text-zinc-400">{sug.reasoning}</p>
                </div>
              </label>
            ))}
            <div className="flex items-center gap-4 mt-2">
               <span className="text-sm text-zinc-500 whitespace-nowrap">Or enter manually:</span>
               <input 
                  type="text" 
                  placeholder="e.g. Frontend Developer"
                  value={selectedRole}
                  onChange={(e) => {
                     setSelectedRole(e.target.value);
                     setRoleSuggestions([]); // Clear suggestions if manually typing something else
                  }}
                  className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#6C63FF] focus:ring-1 focus:ring-[#6C63FF]"
                />
            </div>
          </div>
        ) : (
          <input 
            type="text" 
            placeholder="e.g. Frontend Developer"
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#6C63FF] focus:ring-1 focus:ring-[#6C63FF]"
          />
        )}
      </div>

      {/* Section 2: Location & Search */}
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
              type="text" 
              placeholder="e.g. Sfax, Tunisia OR Remote"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-[#6C63FF] focus:ring-1 focus:ring-[#6C63FF]"
            />
          </div>
          
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-zinc-400">Search Radius</label>
              <span className="text-sm font-mono text-zinc-300">+{radius} km</span>
            </div>
            <input 
              type="range" 
              min="10" 
              max="150" 
              step="10"
              value={radius}
              onChange={(e) => setRadius(parseInt(e.target.value))}
              className="w-full h-2 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-[#6C63FF]"
            />
            <div className="flex justify-between text-xs text-zinc-500 mt-2 font-mono">
              <span>10km</span>
              <span>150km</span>
            </div>
          </div>
        </div>

        <button 
          onClick={handleScrape}
          disabled={!selectedRole || !location || isScraping}
          className="w-full py-3.5 bg-[#6C63FF] hover:bg-[#5B54E6] text-white rounded-xl font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isScraping ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Search className="w-5 h-5" />
          )}
          {isScraping ? 'Searching LinkedIn...' : 'Find Companies'}
        </button>
      </div>

      {/* Section 3: Target Validation */}
      {targets.length > 0 && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                <Target className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Target Validation</h2>
                <p className="text-zinc-500 text-sm">Found {targets.length} matches. Review and confirm.</p>
              </div>
            </div>
            <div className="text-sm">
              <span className="text-emerald-400 font-bold">{selectedTargets.size}</span>
              <span className="text-zinc-500"> / {targets.length} selected</span>
            </div>
          </div>

          <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar pr-2">
            {targets.map((target, idx) => {
              const isSelected = selectedTargets.has(target.company_id);
              return (
                <div 
                  key={target.company_id || idx}
                  className={`flex items-center justify-between p-4 rounded-xl border transition-colors ${
                    isSelected ? 'bg-zinc-800/50 border-zinc-700' : 'bg-zinc-900/50 border-zinc-800/50 opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => toggleTarget(target.company_id)}
                      className={`flex-shrink-0 w-6 h-6 rounded flex items-center justify-center border transition-colors ${
                        isSelected ? 'bg-emerald-500 border-emerald-500 text-white' : 'bg-zinc-800 border-zinc-600'
                      }`}
                    >
                      {isSelected && <Check className="w-4 h-4" />}
                    </button>
                    <div>
                      <h3 className={`font-semibold text-white ${!isSelected && 'line-through text-zinc-500'}`}>
                        {target.company_name}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-zinc-400">{target.job_title}</span>
                        <span className="text-zinc-600">•</span>
                        <span className="text-xs text-zinc-400">{target.location}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className="text-[10px] font-mono tracking-wider uppercase px-2 py-1 bg-zinc-800 rounded text-zinc-400">
                      {target.apply_type.replace('_', ' ')}
                    </span>
                    <a 
                      href={target.job_url} 
                      target="_blank" 
                      rel="noreferrer"
                      className="text-xs text-[#6C63FF] hover:underline"
                    >
                      View Post
                    </a>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-4 flex justify-end">
             <button 
              onClick={handleFinalize}
              disabled={selectedTargets.size === 0}
              className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <CheckCircle2 className="w-5 h-5" />
              Approve & Proceed
              <ChevronRight className="w-4 h-4 ml-1" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

const SparklesIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
    <path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>
  </svg>
);

export default Discovery;
