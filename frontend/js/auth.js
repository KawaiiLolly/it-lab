// Change this if your Django server runs on a different address
const API_BASE = "http://127.0.0.1:8000/api";

// ---------- Token helpers ----------
function saveTokens(access, refresh) {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
}

function getAccessToken() {
    return localStorage.getItem("access_token");
}

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "login.html";
}

// Redirect to login if the user is not logged in. Call at the top of protected pages.
function requireAuth() {
    if (!getAccessToken()) {
        window.location.href = "login.html";
    }
}

// ---------- Signup ----------
async function signupUser(fullName, email, password, rollNo) {
    const res = await fetch(`${API_BASE}/register/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: fullName, email, password, roll_no: rollNo }),
    });
    const data = await res.json();
    return { ok: res.ok, data };
}

// ---------- Login ----------
// The backend's /api/login/ endpoint (Simple JWT) expects a "username" field —
// but this project has no separate username, so we send the email as that value.
async function loginUser(email, password) {
    const res = await fetch(`${API_BASE}/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email, password }),
    });
    const data = await res.json();
    if (res.ok) {
        saveTokens(data.access, data.refresh);
    }
    return { ok: res.ok, data };
}

// ---------- Get logged-in user's profile ----------
async function fetchProfile() {
    const res = await fetch(`${API_BASE}/profile/`, {
        method: "GET",
        headers: { Authorization: `Bearer ${getAccessToken()}` },
    });
    const data = await res.json();
    return { ok: res.ok, data };
}
