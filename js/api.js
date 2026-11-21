/**
 * StarApp Reusable Centralized API Client
 * Communicates with the FastAPI backend over HTTP / JSON with session credentials.
 */
(function(window) {
  "use strict";

  const BASE_URL = window.__STARAPP_API_BASE__ || "";

  class ApiError extends Error {
    constructor(message, status, code, details) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code || "API_ERROR";
      this.details = details || null;
    }
  }

  async function request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint}`;
    const sid = (window.StarAppBridge && typeof window.StarAppBridge.getWindowSessionId === "function")
      ? window.StarAppBridge.getWindowSessionId()
      : sessionStorage.getItem("starapp_window_session_id");
    const headers = {
      "Content-Type": "application/json",
      ...(sid ? { "X-Session-Id": sid } : {}),
      ...(options.headers || {})
    };

    const config = {
      method: options.method || "GET",
      headers: headers,
      credentials: "same-origin", // sends HttpOnly session cookie
    };

    if (options.body && typeof options.body === "object") {
      config.body = JSON.stringify(options.body);
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = (data.error && data.error.message) || data.detail || `Request failed with status ${response.status}`;
        const errorCode = (data.error && data.error.code) || "HTTP_ERROR";
        throw new ApiError(errorMsg, response.status, errorCode, data);
      }

      return data;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(err.message || "Network connection failure", 0, "NETWORK_ERROR");
    }
  }

  const StarAppAPI = {
    // Auth endpoints
    auth: {
      login: (username_or_email, password, selected_role) =>
        request("/api/v1/auth/login", { method: "POST", body: { username_or_email, password, selected_role } }),
      logout: () =>
        request("/api/v1/auth/logout", { method: "POST" }),
      me: () =>
        request("/api/v1/auth/me"),
      switchRole: (role) =>
        request("/api/v1/auth/switch-role", { method: "POST", body: { role } }),
      demoUsers: () =>
        request("/api/v1/auth/demo-users"),
    },

    // Users and Hierarchy
    users: {
      list: (band, track) => {
        let q = [];
        if (band) q.push(`band=${encodeURIComponent(band)}`);
        if (track) q.push(`track=${encodeURIComponent(track)}`);
        const query = q.length ? `?${q.join("&")}` : "";
        return request(`/api/v1/users/${query}`);
      },
      getProfile: (userId) =>
        request(`/api/v1/users/${userId}`),
      getEligibleReviewers: (badgeBand) =>
        request(`/api/v1/users/eligible-reviewers/${badgeBand}`),
      getHierarchyTree: () =>
        request("/api/v1/users/hierarchy/tree"),
    },

    // Bands & Taxonomy
    bands: {
      list: () =>
        request("/api/v1/bands/"),
      taxonomy: () =>
        request("/api/v1/bands/taxonomy"),
      addCapability: (name) =>
        request("/api/v1/bands/capabilities", { method: "POST", body: { name } }),
      addSkill: (name, capability_name) =>
        request("/api/v1/bands/skills", { method: "POST", body: { name, capability_name } }),
    },

    // Badges
    badges: {
      list: (band, status) => {
        let q = [];
        if (band) q.push(`band=${encodeURIComponent(band)}`);
        if (status) q.push(`status=${encodeURIComponent(status)}`);
        const query = q.length ? `?${q.join("&")}` : "";
        return request(`/api/v1/badges/${query}`);
      },
      get: (badgeId) =>
        request(`/api/v1/badges/${badgeId}`),
      create: (badgeData) =>
        request("/api/v1/badges/", { method: "POST", body: badgeData }),
      update: (badgeId, updates) =>
        request(`/api/v1/badges/${badgeId}`, { method: "PUT", body: updates }),
    },

    // Reviews & Approval
    reviews: {
      request: (badgeId, reviewerId, notes) =>
        request("/api/v1/reviews/request", { method: "POST", body: { badge_id: badgeId, reviewer_id: reviewerId, notes } }),
      inbox: () =>
        request("/api/v1/reviews/inbox"),
      guardianOverview: () =>
        request("/api/v1/reviews/guardian-overview"),
      submitDecision: (badgeId, decisionData) =>
        request(`/api/v1/reviews/${badgeId}/decision`, { method: "POST", body: decisionData }),
    },

    // Allotments & Roadmaps
    allotments: {
      allot: (badgeId, cosmonautIds, timeline) =>
        request("/api/v1/allotments/", { method: "POST", body: { badge_id: badgeId, cosmonaut_ids: cosmonautIds, timeline } }),
      roadmap: () =>
        request("/api/v1/allotments/roadmap"),
      guardianOverview: () =>
        request("/api/v1/allotments/guardian-overview"),
      requestExtension: (badgeId, proposedDeadline, reason) =>
        request("/api/v1/allotments/extensions/request", { method: "POST", body: { badge_id: badgeId, proposed_deadline: proposedDeadline, reason } }),
      listExtensions: (status) => {
        const query = status ? `?status=${encodeURIComponent(status)}` : "";
        return request(`/api/v1/allotments/extensions${query}`);
      },
      decideExtension: (extensionId, status, notes) =>
        request(`/api/v1/allotments/extensions/${extensionId}/decision`, { method: "POST", body: { status, response_notes: notes } }),
    },

    // Submissions
    submissions: {
      submit: (submissionData) =>
        request("/api/v1/submissions/", { method: "POST", body: submissionData }),
      history: (badgeId) =>
        request(`/api/v1/submissions/history/${badgeId}`),
      pending: () =>
        request("/api/v1/submissions/pending"),
    },

    // Evaluations & Marksheets
    evaluations: {
      submit: (evalData) =>
        request("/api/v1/evaluations/", { method: "POST", body: evalData }),
      marksheets: (badgeId) => {
        const query = badgeId ? `?badge_id=${encodeURIComponent(badgeId)}` : "";
        return request(`/api/v1/evaluations/marksheets${query}`);
      },
      leaderboard: () =>
        request("/api/v1/evaluations/leaderboard"),
    },

    // External Integrations & Gemini AI
    gemini: {
      generateBadge: (band, power, capability, skill, outcome_sentence) =>
        request("/api/v1/integrations/gemini/generate-badge", {
          method: "POST",
          body: { band, power, capability, skill, outcome_sentence }
        }),
      mentorChat: (message, badge_title, context) =>
        request("/api/v1/integrations/gemini/mentor-chat", {
          method: "POST",
          body: { message, badge_title, context }
        }),
    },

    // System Health & Diagnostics
    system: {
      health: () => request("/api/health"),
      auditLogs: (limit = 50) => request(`/api/v1/audit/logs?limit=${limit}`),
    }
  };

  window.StarAppAPI = StarAppAPI;
})(window);
