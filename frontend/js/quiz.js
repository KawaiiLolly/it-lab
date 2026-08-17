// ---------- Check this user's attempt status (for dashboard / instructions) ----------
async function fetchQuizStatus() {
    const res = await fetch(`${API_BASE}/quiz/status/`, {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
    });
    const data = await res.json();
    return { ok: res.ok, data };
}

// ---------- Start (or resume) the one allowed test attempt ----------
async function startQuiz() {
    const res = await fetch(`${API_BASE}/quiz/start/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getAccessToken()}` },
    });
    const data = await res.json();
    return { ok: res.ok, data };
}

// ---------- Get a session's questions + remaining time ----------
async function fetchSession(sessionId) {
    const res = await fetch(`${API_BASE}/quiz/session/${sessionId}/`, {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
    });
    const data = await res.json();
    return { ok: res.ok, data };
}

// ---------- Save (or clear, if selectedOption is null) an answer ----------
async function saveAnswer(sessionId, questionId, selectedOption) {
    const res = await fetch(`${API_BASE}/quiz/session/${sessionId}/answer/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAccessToken()}`,
        },
        body: JSON.stringify({ question_id: questionId, selected_option: selectedOption }),
    });
    const data = await res.json();
    return { ok: res.ok, data };
}

// ---------- Toggle a question's bookmark flag ----------
async function toggleBookmark(sessionId, questionId, bookmarked) {
    const res = await fetch(`${API_BASE}/quiz/session/${sessionId}/bookmark/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAccessToken()}`,
        },
        body: JSON.stringify({ question_id: questionId, bookmarked: bookmarked }),
    });
    const data = await res.json();
    return { ok: res.ok, data };
}

// ---------- Submit / finish the test ----------
async function submitQuiz(sessionId) {
    const res = await fetch(`${API_BASE}/quiz/session/${sessionId}/submit/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getAccessToken()}` },
    });
    const data = await res.json();
    return { ok: res.ok, data };
}
