import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';

/**
 * Custom hook to manage profile state.
 * Fetches profile and completeness from backend.
 */
export const useProfile = () => {
  const [profile, setProfile] = useState(null);
  const [completeness, setCompleteness] = useState({ score: 0, missing_fields: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [profileData, completenessData] = await Promise.all([
        apiClient.getProfile(),
        apiClient.getCompleteness(),
      ]);
      setProfile(profileData);
      setCompleteness(completenessData);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error("Failed to load profile:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const updateProfile = useCallback(async (updates) => {
    try {
      const updated = await apiClient.updateProfile(updates);
      setProfile(updated);
      // Re-fetch completeness after update
      const newCompleteness = await apiClient.getCompleteness();
      setCompleteness(newCompleteness);
      return updated;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  return {
    profile,
    loading,
    error,
    completenessScore: completeness.score,
    missingFields: completeness.missing_fields,
    updateProfile,
    refreshProfile: fetchAll,
  };
};
