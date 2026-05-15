export const BASE_URL = "http://localhost:8000/api";

const request = async (endpoint, options = {}) => {
  const url = `${BASE_URL}${endpoint}`;
  const config = {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  };
  const response = await fetch(url, config);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Something went wrong");
  }
  return data;
};

export const apiClient = {
  // Profile
  getProfile: () => request("/profile/"),
  updateProfile: (data) => request("/profile/", { method: "PATCH", body: JSON.stringify(data) }),
  getCompleteness: () => request("/profile/completeness"),

  // Discovery
  suggestRoles: () => request("/discovery/suggest-roles"),
  scrapeJobs: (params) => request("/discovery/scrape", { method: "POST", body: JSON.stringify(params) }),
  getTargets: () => request("/discovery/targets"),
  finalizeTargets: (ids) => request("/discovery/targets/finalize", { method: "POST", body: JSON.stringify({ ids }) }),
  addManualTarget: (data) => request("/discovery/targets/manual", { method: "POST", body: JSON.stringify(data) }),
  deleteTarget: (companyId) => request(`/discovery/targets/${companyId}`, { method: "DELETE" }),

  // Generation
  generateCV: (companyId) => request(`/generation/cv/generate/${companyId}`, { method: "POST" }),
  getCVJson: (companyId) => request(`/generation/cv/json/${companyId}`),
  updateCVJson: (companyId, data) => request(`/generation/cv/${companyId}`, { method: "PATCH", body: JSON.stringify(data) }),
  optimizeCV: (data) => request("/generation/cv/optimize", { method: "POST", body: JSON.stringify(data) }),
  generateCoverLetter: (companyId) => request(`/generation/cover-letter/generate/${companyId}`, { method: "POST" }),
  getCLJson: (companyId) => request(`/generation/cover-letter/json/${companyId}`),
  updateCLJson: (companyId, data) => request(`/generation/cover-letter/${companyId}`, { method: "PATCH", body: JSON.stringify(data) }),
  getApplicationMeta: (companyId) => request(`/generation/meta/${companyId}`),
  getGANIterations: (companyId) => request(`/generation/iterations/${companyId}`),
  explainInsight: (companyId, insightType, insightValue) =>
    request(`/generation/explain/${companyId}`, {
      method: "POST",
      body: JSON.stringify({ insight_type: insightType, insight_value: insightValue }),
    }),

  // Apply
  getApplyStatus: () => request("/apply/status"),
  applyToCompany: (companyId) => request(`/apply/run/${companyId}`, { method: "POST" }),

  // History
  getHistory: () => request("/history/"),
  updateHistoryStatus: (companyId, status) =>
    request(`/history/${companyId}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),

  // Interview
  startInterviewSession: (companyId) => request(`/interview/${companyId}/start`, { method: "POST" }),
  sendInterviewMessage: (companyId, sessionId, message) =>
    request(`/interview/${companyId}/${sessionId}/message`, { method: "POST", body: JSON.stringify({ message }) }),
  endInterviewSession: (companyId, sessionId) => request(`/interview/${companyId}/${sessionId}/end`, { method: "POST" }),
  getInterviewSessions: (companyId) => request(`/interview/${companyId}/sessions`),
  clearInterviewSessions: (companyId) => request(`/interview/${companyId}/sessions`, { method: "DELETE" }),
  getInterviewHelp: (companyId, sessionId) => request(`/interview/${companyId}/${sessionId}/help`, { method: "POST" }),
};
