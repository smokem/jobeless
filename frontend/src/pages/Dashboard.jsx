import React, { useState, useEffect } from 'react';
import { useProfile } from '../hooks/useProfile';
import ProfileCard from '../components/ProfileCard';
import { apiClient } from '../api/client';
import { Inbox, Building2, Calendar, Star, MoreHorizontal } from 'lucide-react';

/**
 * Dashboard page — Profile overview + application history table.
 */
const Dashboard = () => {
  const { profile, loading, completenessScore, missingFields, updateProfile, refreshProfile } = useProfile();
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await apiClient.getHistory();
        setHistory(data || []);
      } catch (err) {
        // History endpoint may not be implemented yet — fail silently
        console.warn("History not available:", err.message);
        setHistory([]);
      } finally {
        setHistoryLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const statusColors = {
    sent: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    opened: 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400',
    replied: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    interview: 'bg-purple-500/10 border-purple-500/20 text-purple-400',
    rejected: 'bg-red-500/10 border-red-500/20 text-red-400',
    pending: 'bg-zinc-500/10 border-zinc-500/20 text-zinc-400',
  };

  return (
    <div className="space-y-8">
      {/* Section title */}
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Dashboard</h1>
        <p className="text-zinc-500 text-sm mt-1">Your job application command center</p>
      </div>

      {/* Profile Card */}
      <ProfileCard
        profile={profile}
        completenessScore={completenessScore}
        missingFields={missingFields}
        onUpdate={updateProfile}
        onRefresh={refreshProfile}
        loading={loading}
      />

      {/* Application History */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-white">Application History</h2>
          <p className="text-zinc-500 text-xs mt-1 uppercase tracking-wider font-mono">
            {history.length} application{history.length !== 1 ? 's' : ''} tracked
          </p>
        </div>

        {historyLoading ? (
          <div className="p-12 text-center">
            <div className="w-8 h-8 border-2 border-zinc-700 border-t-[#6C63FF] rounded-full animate-spin mx-auto" />
            <p className="text-zinc-500 text-sm mt-4">Loading history...</p>
          </div>
        ) : history.length === 0 ? (
          /* Empty state */
          <div className="p-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 border border-zinc-700 flex items-center justify-center mx-auto mb-4">
              <Inbox className="w-8 h-8 text-zinc-600" />
            </div>
            <h3 className="text-lg font-semibold text-zinc-300 mb-2">No applications yet</h3>
            <p className="text-zinc-500 text-sm max-w-sm mx-auto">
              Start in <span className="text-[#6C63FF] font-medium">Discover</span> to find jobs and begin your automated application pipeline.
            </p>
          </div>
        ) : (
          /* History table */
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider border-b border-zinc-800">
                  <th className="px-6 py-4 font-medium">Company</th>
                  <th className="px-6 py-4 font-medium">Role</th>
                  <th className="px-6 py-4 font-medium">Date Sent</th>
                  <th className="px-6 py-4 font-medium">Score</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {history.map((app, idx) => (
                  <tr key={`${app.company_id || 'entry'}_${idx}`} className="hover:bg-zinc-800/20 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center">
                          <Building2 className="w-4 h-4 text-zinc-500" />
                        </div>
                        <span className="text-sm font-medium text-white">{app.company_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-zinc-400">{app.job_title}</td>
                    <td className="px-6 py-4 text-sm text-zinc-500 font-mono">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(app.date_sent).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        <Star className="w-3.5 h-3.5 text-amber-500" />
                        <span className="text-sm font-mono text-amber-400">{app.cv_score_achieved}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wider border ${statusColors[app.status] || statusColors.pending}`}>
                        {app.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button className="p-1.5 rounded-lg hover:bg-zinc-800 transition-colors">
                        <MoreHorizontal className="w-4 h-4 text-zinc-500" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
