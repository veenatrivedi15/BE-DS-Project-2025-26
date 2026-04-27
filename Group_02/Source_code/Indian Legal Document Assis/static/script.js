let originalDraft = "";
let placeholderValues = {};

// ================== NAVIGATION ==================
function goLogin() {
    window.location.href = "/login";   // ✅ FIXED
}

function goRegister() {
    window.location.href = "/register";  // ✅ FIXED
}

async function logout() {
    await fetch("/logout");
    window.location.href = "/login";
}

// ================== PLACEHOLDERS ==================
function extractPlaceholders(text) {
    const regex = /\[([^\]]+)\]/g;
    const set = new Set();
    let match;

    while ((match = regex.exec(text)) !== null) {
        set.add(match[1]);
    }

    return Array.from(set);
}

function generatePlaceholderInputs(draftText) {
    const container = document.getElementById("placeholders");
    container.innerHTML = "";
    placeholderValues = {};

    const placeholders = extractPlaceholders(draftText);

    placeholders.forEach(ph => {
        const label = document.createElement("label");
        label.textContent = ph;

        const input = document.createElement("input");
        input.placeholder = ph;
        input.type = detectFieldType(ph);  // ✅ FIXED

        input.addEventListener("input", (e) => {
            placeholderValues[ph] = e.target.value;
            applyAllPlaceholders();
        });

        container.appendChild(label);
        container.appendChild(input);
    });
}

function detectFieldType(name) {
    const n = name.toLowerCase();
    if (n.includes("date")) return "date";
    if (n.includes("amount") || n.includes("rupees")) return "number";
    if (n.includes("phone")) return "tel";
    return "text";
}

function applyAllPlaceholders() {
    let updatedDraft = originalDraft;

    for (const key in placeholderValues) {
        const regex = new RegExp(`\\[${key}\\]`, "g");
        updatedDraft = updatedDraft.replace(regex, placeholderValues[key]);
    }

    document.getElementById("draft").value = updatedDraft;
}

// ================== AI ==================
async function identifyDoc() {
    const issue = document.getElementById("issue").value;

    const res = await fetch("/stage1", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ issue })
    });

    const data = await res.json();
    document.getElementById("docName").innerText = data.document_name;
}

async function generateDraft() {
    const issue = document.getElementById("issue").value;

    const res = await fetch("/stage2", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ issue })
    });

    const data = await res.json();

    originalDraft = data.draft;
    document.getElementById("draft").value = originalDraft;

    generatePlaceholderInputs(originalDraft);
}

// ================== EXPORT ==================
async function exportFile(type) {
    const text = document.getElementById("draft").value;

    const res = await fetch(`/export/${type}`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({ text })
    });

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `document.${type}`;
    a.click();
}

async function sendForVerification() {
    const issue = document.getElementById("issue").value;
    const draft = document.getElementById("draft").value;

    if (!issue || !draft) {
        alert("Generate document first!");
        return;
    }

    const res = await fetch("/save_document", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            issue: issue,
            draft: draft
        })
    });

    const data = await res.json();

    if (res.ok) {
        alert("Sent for verification ✅");
    } else {
        alert("Error sending document ❌");
    }
}

async function logout() {
    const res = await fetch("/logout");

    if (res.ok) {
        window.location.href = "/login-page";   // 🔥 redirect after logout
    } else {
        alert("Logout failed ❌");
    }
}

function goDashboard() {
    window.location.href = "/lawyer-dashboard";
} 

async function loadAllDocs() {
    const res = await fetch("/lawyer/all-documents");
    const data = await res.json();

    renderDocs(data.documents);
}

async function loadDocs() {
    const res = await fetch("/lawyer/documents");
    const data = await res.json();

    renderDocs(data.documents);
}