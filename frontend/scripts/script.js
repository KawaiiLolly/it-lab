const API = "http://127.0.0.1:8000/api";


// LOGIN

const loginForm = document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const username =
            document.getElementById("username").value;

        const password =
            document.getElementById("password").value;


        const response = await fetch(`${API}/login/`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username: username,
                password: password
            })

        });


        const data = await response.json();


        if (response.ok) {

            localStorage.setItem(
                "access",
                data.access
            );

            localStorage.setItem(
                "refresh",
                data.refresh
            );

            window.location.href = "dashboard.html";

        } else {

            document.getElementById("message")
                .innerText = "Invalid username or password";

        }

    });

}

// SIGNUP

const signupForm =
    document.getElementById("signupForm");


if (signupForm) {

    signupForm.addEventListener("submit", async function(event) {

        event.preventDefault();


        const username =
            document.getElementById("signupUsername").value;

        const email =
            document.getElementById("signupEmail").value;

        const password =
            document.getElementById("signupPassword").value;


        const response = await fetch(`${API}/signup/`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                username: username,
                email: email,
                password: password
            })

        });


        const data = await response.json();


        if (response.ok) {

            document.getElementById("signupMessage")
                .innerText = "Account created successfully!";

            setTimeout(function() {

                window.location.href = "index.html";

            }, 1000);

        } else {

            document.getElementById("signupMessage")
                .innerText = JSON.stringify(data);

        }

    });

}

// DASHBOARD

const profileUsername  =
    document.getElementById("profileUsername");


if (profileUsername ) {

    const token =
        localStorage.getItem("access");


    if (!token) {

        window.location.href = "index.html";

    }


    fetch(`${API}/profile/`, {

        method: "GET",

        headers: {
            "Authorization": `Bearer ${token}`
        }

    })

    .then(response => {

        if (!response.ok) {

            throw new Error("Unauthorized");

        }

        return response.json();

    })

    .then(data => {

        document.getElementById("profileUsername")
            .innerText = data.username;

        document.getElementById("profileEmail")
            .innerText = data.email;

    })

    .catch(error => {

        localStorage.removeItem("access");
        localStorage.removeItem("refresh");

        window.location.href = "index.html";

    });

}

// LOGOUT

const logoutBtn =
    document.getElementById("logoutBtn");


if (logoutBtn) {

    logoutBtn.addEventListener("click", function() {

        localStorage.removeItem("access");

        localStorage.removeItem("refresh");

        window.location.href = "index.html";

    });

}