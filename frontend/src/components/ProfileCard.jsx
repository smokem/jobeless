import React, { useState } from 'react';
import { User, MapPin, Briefcase, Sparkles, X, Check, AlertCircle } from 'lucide-react';

/**
 * ProfileCard — Reusable component displaying profile overview with
 * completeness score, missing field chips, and inline editing.
 *
 * Props:
 *   profile       — the full profile object
 *   completenessScore — float 0-100
 *   missingFields — array of missing field label strings
 *   onUpdate      — async (updates) => void — called to PATCH profile
 *   loading       — boolean
 */
const ProfileCard = ({ profile, completenessScore, missingFields, onUpdate, loading }) => {
  const [editingField, setEditingField] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  if (loading) {
    return (
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-8 animate-pulse">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 rounded-full bg-zinc-800" />
          <div className="flex-1 space-y-3">
            <div className="h-6 bg-zinc-800 rounded w-48" />
            <div className="h-4 bg-zinc-800 rounded w-64" />
            <div className="h-3 bg-zinc-800 rounded w-32" />
          </div>
        </div>
      </div>
    );
  }

  if (!profile) return null;

  const personalInfo = profile.personal_info || {};
  const contact = personalInfo.contact || {};
  const location = personalInfo.location || {};
  const fullName = personalInfo.full_name || 'Unknown';
  const headline = personalInfo.headline || '';
  const city = location.city || '';
  const country = location.country || '';
  const locationStr = [city, country].filter(Boolean).join(', ');
  const avatarUrl = contact.profile_picture;

  // Color logic for progress bar
  const getBarColor = (score) => {
    if (score >= 80) return { bar: 'bg-emerald-500', glow: 'shadow-emerald-500/20', text: 'text-emerald-400' };
    if (score >= 50) return { bar: 'bg-amber-500', glow: 'shadow-amber-500/20', text: 'text-amber-400' };
    return { bar: 'bg-red-500', glow: 'shadow-red-500/20', text: 'text-red-400' };
  };

  const colors = getBarColor(completenessScore);

  // Map missing field labels to the PATCH update path
  const fieldEditMap = {
    email: { path: 'personal_info.contact.email', label: 'Email', placeholder: 'you@example.com' },
    phone: { path: 'personal_info.contact.phone', label: 'Phone', placeholder: '+1234567890' },
    github_url: { path: 'personal_info.contact.github', label: 'GitHub URL', placeholder: 'https://github.com/...' },
    portfolio_url: { path: 'personal_info.contact.portfolio', label: 'Portfolio URL', placeholder: 'https://...' },
    linkedin_url: { path: 'personal_info.contact.linkedin', label: 'LinkedIn URL', placeholder: 'https://linkedin.com/in/...' },
    headline: { path: 'personal_info.headline', label: 'Headline', placeholder: 'e.g. Full-Stack Developer' },
    summary: { path: 'personal_info.summary', label: 'Summary', placeholder: 'Brief professional summary...' },
    location_city: { path: 'personal_info.location.city', label: 'City', placeholder: 'e.g. San Francisco' },
    languages: { path: 'personal_info.languages', label: 'Languages', placeholder: 'Cannot edit inline' },
    full_name: { path: 'personal_info.full_name', label: 'Full Name', placeholder: 'First Last' },
    exact_education_dates: { path: null, label: 'Education Dates', placeholder: 'Edit in profile.json' },
    gpa: { path: null, label: 'GPA', placeholder: 'Edit in profile.json' },
    education: { path: null, label: 'Education', placeholder: 'Edit in profile.json' },
    work_experience: { path: null, label: 'Work Experience', placeholder: 'Edit in profile.json' },
    skills: { path: null, label: 'Skills', placeholder: 'Edit in profile.json' },
    projects: { path: null, label: 'Projects', placeholder: 'Edit in profile.json' },
    certifications: { path: null, label: 'Certifications', placeholder: 'Edit in profile.json' },
    personality_and_work_style: { path: null, label: 'Personality', placeholder: 'Edit in profile.json' },
    preferences_and_goals: { path: null, label: 'Preferences', placeholder: 'Edit in profile.json' },
    cv_generation_hints: { path: null, label: 'CV Hints', placeholder: 'Edit in profile.json' },
  };

  const handleChipClick = (field) => {
    const config = fieldEditMap[field];
    if (!config?.path) return; // non-editable
    setEditingField(field);
    setEditValue('');
  };

  const handleSave = async () => {
    if (!editingField || !editValue.trim()) return;
    const config = fieldEditMap[editingField];
    if (!config?.path) return;

    setSaving(true);
    try {
      // Build nested update object from dot-path
      const parts = config.path.split('.');
      const update = {};
      let current = update;
      for (let i = 0; i < parts.length - 1; i++) {
        current[parts[i]] = {};
        current = current[parts[i]];
      }
      current[parts[parts.length - 1]] = editValue.trim();

      await onUpdate(update);
      setEditingField(null);
      setEditValue('');
    } catch (err) {
      console.error('Failed to update field:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditingField(null);
    setEditValue('');
  };

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl overflow-hidden">
      {/* Gradient top accent */}
      <div className="h-1 bg-gradient-to-r from-[#6C63FF] via-purple-500 to-pink-500" />

      <div className="p-8">
        {/* Profile header */}
        <div className="flex items-start gap-6 mb-6">
          {/* Avatar */}
          <div className="relative flex-shrink-0">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={fullName}
                className="w-20 h-20 rounded-full object-cover border-2 border-zinc-700 shadow-lg"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-zinc-800 border-2 border-zinc-700 flex items-center justify-center">
                <User className="w-8 h-8 text-zinc-500" />
              </div>
            )}
            <div className={`absolute -bottom-1 -right-1 w-6 h-6 rounded-full ${colors.bar} flex items-center justify-center shadow-lg ${colors.glow}`}>
              <Sparkles className="w-3 h-3 text-white" />
            </div>
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h2 className="text-2xl font-bold text-white tracking-tight truncate">{fullName}</h2>
            {headline && (
              <p className="text-zinc-400 mt-1 flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                <span className="truncate">{headline}</span>
              </p>
            )}
            {locationStr && (
              <p className="text-zinc-500 text-sm mt-1 flex items-center gap-2">
                <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{locationStr}</span>
              </p>
            )}
          </div>

          {/* Score badge */}
          <div className={`flex-shrink-0 px-4 py-2 rounded-xl border ${
            completenessScore >= 80
              ? 'bg-emerald-500/10 border-emerald-500/20'
              : completenessScore >= 50
                ? 'bg-amber-500/10 border-amber-500/20'
                : 'bg-red-500/10 border-red-500/20'
          }`}>
            <div className={`text-2xl font-bold font-mono ${colors.text}`}>
              {completenessScore}%
            </div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 text-center">
              Complete
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Profile Completeness</span>
            <span className={`text-xs font-mono ${colors.text}`}>{completenessScore}/100</span>
          </div>
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className={`h-full ${colors.bar} rounded-full transition-all duration-1000 ease-out shadow-lg ${colors.glow}`}
              style={{ width: `${completenessScore}%` }}
            />
          </div>
        </div>

        {/* Missing fields chips */}
        {missingFields && missingFields.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="w-4 h-4 text-zinc-500" />
              <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Missing Fields</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {missingFields.map((field) => {
                const config = fieldEditMap[field] || { label: field };
                const isEditable = config?.path;

                return (
                  <button
                    key={field}
                    onClick={() => isEditable && handleChipClick(field)}
                    disabled={!isEditable}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                      isEditable
                        ? 'bg-[#6C63FF]/10 border border-[#6C63FF]/20 text-[#6C63FF] hover:bg-[#6C63FF]/20 hover:border-[#6C63FF]/40 cursor-pointer'
                        : 'bg-zinc-800/50 border border-zinc-700/50 text-zinc-500 cursor-default'
                    }`}
                  >
                    {config.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Inline edit form */}
        {editingField && (
          <div className="mt-4 p-4 bg-zinc-800/50 border border-zinc-700 rounded-xl animate-in slide-in-from-top-2">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm font-medium text-white">
                Edit: {fieldEditMap[editingField]?.label}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder={fieldEditMap[editingField]?.placeholder}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-[#6C63FF]/50 focus:border-[#6C63FF]/50 transition-all"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && handleSave()}
              />
              <button
                onClick={handleSave}
                disabled={saving || !editValue.trim()}
                className="p-2.5 bg-[#6C63FF] hover:bg-[#5B54E6] rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Check className="w-4 h-4 text-white" />
                )}
              </button>
              <button
                onClick={handleCancel}
                className="p-2.5 bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-zinc-300" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfileCard;
