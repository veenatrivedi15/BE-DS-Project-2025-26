// dashboard.js

document.addEventListener('DOMContentLoaded', () => {

    // ===== NAVBAR SCROLL EFFECT =====
    const siteHeader = document.getElementById('site-header') || document.querySelector('.header');
    if (siteHeader) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 10) {
                siteHeader.classList.add('scrolled');
            } else {
                siteHeader.classList.remove('scrolled');
            }
        }, { passive: true });
    }

    // ===== HAMBURGER MENU TOGGLE =====
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (hamburgerBtn && mobileMenu) {
        hamburgerBtn.addEventListener('click', function () {
            const isOpen = hamburgerBtn.classList.toggle('is-open');
            mobileMenu.classList.toggle('is-open');
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });

        mobileMenu.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                hamburgerBtn.classList.remove('is-open');
                mobileMenu.classList.remove('is-open');
                document.body.style.overflow = '';
            });
        });

        window.addEventListener('resize', function () {
            if (window.innerWidth > 768) {
                hamburgerBtn.classList.remove('is-open');
                mobileMenu.classList.remove('is-open');
                document.body.style.overflow = '';
            }
        });
    }

    // 1. Initialize User Profile in Navbar
    const username = localStorage.getItem('username');
    const role = localStorage.getItem('role') || 'User';

    if (username) {
        // Update Navbar
        const navUserSection = document.getElementById('nav-user-section');
        if (navUserSection) {
            navUserSection.style.display = 'flex';
            navUserSection.style.alignItems = 'center';
            navUserSection.innerHTML = `
                <div class="user-profile-info" style="display:flex;align-items:center;gap:8px;">
                    <span class="profile-icon">👤</span>
                    <span class="profile-name" style="color:#c8e6c9;font-weight:600;">${username}</span>
                </div>
                <button onclick="logout()" class="btn-signin" style="margin-left:12px;font-size:0.82rem;padding:6px 14px;cursor:pointer;">Logout</button>
            `;
        }

        // Update Dashboard Header
        const userDisplayName = document.getElementById('user-display-name');
        const userRoleBadge = document.getElementById('user-role-badge');
        
        if (userDisplayName) userDisplayName.innerText = username;
        if (userRoleBadge) userRoleBadge.innerText = role.charAt(0).toUpperCase() + role.slice(1);
    }

    // 2. Fetch User Listings
    console.log("Fetching listings for:", username);
    fetchUserListings();
});

function logout() {
    if (confirm("Are you sure you want to logout?")) {
        localStorage.clear();
        window.location.href = '/';
    }
}

// Log to verify script load
console.log("Dashboard script loaded");

// ==========================================
// 1. FETCH & DISPLAY LISTINGS
// ==========================================
async function fetchUserListings() {
    const username = localStorage.getItem('username');
    const role = localStorage.getItem('role') || 'user';
    const grid = document.getElementById('my-listings');

    try {
        const response = await fetch(`/api/marketplace/my-list?username=${username}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        const products = await response.json();

        if (products.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 60px; background: rgba(74, 124, 89, 0.1); border-radius: 15px; border: 2px dashed rgba(74, 124, 89, 0.3);">
                    <div style="font-size: 3rem; margin-bottom: 15px;">🍃</div>
                    <h3 style="color: #b6f5b6; margin-bottom: 10px;">No listings yet</h3>
                    <p style="color: #9fbfb0;">Start by adding your crops, fertilizers, or equipment!</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = products.map(item => `
            <div class="listing-card">
                <div class="listing-header">
                    <span class="listing-badge">${item.category} • ${item.mode}</span>
                    <span style="color: #9fbfb0; font-size: 0.9rem;">${new Date(item.created_at).toLocaleDateString()}</span>
                </div>
                
                <h3 style="color: white; margin-bottom: 8px; font-size: 1.3rem;">${item.name}</h3>
                <div class="listing-price">₹${item.price}</div>
                
                <p style="color: #c8e6c9; font-size: 0.95rem; margin-bottom: 15px; line-height: 1.4;">
                    ${item.description.substring(0, 80)}${item.description.length > 80 ? '...' : ''}
                </p>
                
                <div style="background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 8px; margin-bottom: 5px; font-size: 0.9rem;">
                    <span style="color: #6b9c7a;">Quantity:</span> <span style="color: white;">${item.quantity}</span>
                </div>

                <div class="listing-actions">
                    <button onclick="editItem('${item._id}')" class="action-btn btn-edit">✏️ Edit</button>
                    <button onclick="deleteItem('${item._id}')" class="action-btn btn-delete">🗑️ Delete</button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error("Error fetching listings:", error);
        grid.innerHTML = '<p style="color: #e74c3c;">Error loading your listings. Please try again later.</p>';
    }
}

// ==========================================
// 2. MODAL LOGIC
// ==========================================
const modal = document.getElementById('itemModal');
const itemForm = document.getElementById('itemForm');

function openAddModal() {
    console.log("Opening add modal");
    document.getElementById('modalTitle').innerText = "Add New Listing";
    document.getElementById('itemId').value = ""; // Clear ID for new item
    itemForm.reset();
    modal.style.display = 'flex';
}

function closeModal() {
    modal.style.display = 'none';
}

// Close modal if clicking outside
window.onclick = function (event) {
    if (event.target == modal) {
        closeModal();
    }
}

// ==========================================
// 3. ADD / UPDATE ITEM
// ==========================================
itemForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const itemId = document.getElementById('itemId').value;
    const isEdit = !!itemId;

    const formData = {
        name: document.getElementById('itemName').value,
        price: parseFloat(document.getElementById('itemPrice').value),
        category: document.getElementById('itemCategory').value,
        mode: document.getElementById('itemMode').value,
        quantity: document.getElementById('itemQuantity').value,
        description: document.getElementById('itemDesc').value,
        username: localStorage.getItem('username'),
        role: localStorage.getItem('role') || 'user'
    };

    const url = isEdit
        ? `/api/marketplace/update/${itemId}`
        : '/api/marketplace/add';

    const method = isEdit ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            alert(result.message);
            closeModal();
            fetchUserListings(); // Refresh list
        } else {
            alert(result.message || "Operation failed");
        }

    } catch (error) {
        console.error("Error submitting form:", error);
        alert("Something went wrong");
    }
});

// ==========================================
// 4. DELETE ITEM
// ==========================================
async function deleteItem(id) {
    if (!confirm("Are you sure you want to delete this listing?")) return;

    try {
        const response = await fetch(`/api/marketplace/delete/${id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: localStorage.getItem('username'),
                role: localStorage.getItem('role') || 'user'
            })
        });

        const result = await response.json();

        if (response.ok) {
            alert(result.message);
            fetchUserListings(); // Refresh list
        } else {
            alert(result.message);
        }

    } catch (error) {
        console.error("Error deleting item:", error);
        alert("Error deleting item");
    }
}

// ==========================================
// 5. EDIT PRE-FILL (Fetch Current Data)
// ==========================================
// Note: In a real app we might fetch specific item details from server.
// For now, we'll just implement a basic edit that needs re-population or we fetch all again.
// To keep it simple, we will just set the ID and let user re-enter or we find from DOM.
// Better approach: We passed ID, let's filter from the current list (client-side) to pre-fill.

// We need to store the fetched products globally to access them for editing.
// Let's refactor fetchUserListings slightly to store data.
let currentUserProducts = [];

// Monkey-patch fetchUserListings to save state
const originalFetch = fetchUserListings;
fetchUserListings = async function () {
    const username = localStorage.getItem('username');
    try {
        const response = await fetch(`/api/marketplace/my-list?username=${username}`);
        currentUserProducts = await response.json();

        // Use the same rendering logic
        const grid = document.getElementById('my-listings');
        if (currentUserProducts.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 60px; background: rgba(74, 124, 89, 0.1); border-radius: 15px; border: 2px dashed rgba(74, 124, 89, 0.3);">
                    <div style="font-size: 3rem; margin-bottom: 15px;">🍃</div>
                    <h3 style="color: #b6f5b6; margin-bottom: 10px;">No listings yet</h3>
                    <p style="color: #9fbfb0;">Start by adding your crops, fertilizers, or equipment!</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = currentUserProducts.map(item => `
            <div class="listing-card">
                <div class="listing-header">
                    <span class="listing-badge">${item.category} • ${item.mode}</span>
                    <span style="color: #9fbfb0; font-size: 0.9rem;">${new Date(item.created_at).toLocaleDateString()}</span>
                </div>
                
                <h3 style="color: white; margin-bottom: 8px; font-size: 1.3rem;">${item.name}</h3>
                <div class="listing-price">₹${item.price}</div>
                
                <p style="color: #c8e6c9; font-size: 0.95rem; margin-bottom: 15px; line-height: 1.4;">
                    ${item.description.substring(0, 80)}${item.description.length > 80 ? '...' : ''}
                </p>
                
                <div style="background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 8px; margin-bottom: 5px; font-size: 0.9rem;">
                    <span style="color: #6b9c7a;">Quantity:</span> <span style="color: white;">${item.quantity}</span>
                </div>

                <div class="listing-actions">
                    <button onclick="editItem('${item._id}')" class="action-btn btn-edit">✏️ Edit</button>
                    <button onclick="deleteItem('${item._id}')" class="action-btn btn-delete">🗑️ Delete</button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error(error);
    }
}

function editItem(id) {
    const item = currentUserProducts.find(p => p._id === id);
    if (!item) return;

    document.getElementById('modalTitle').innerText = "Edit Listing";
    document.getElementById('itemId').value = item._id;

    document.getElementById('itemName').value = item.name;
    document.getElementById('itemPrice').value = item.price;
    document.getElementById('itemCategory').value = item.category;
    document.getElementById('itemMode').value = item.mode;
    document.getElementById('itemQuantity').value = item.quantity;
    document.getElementById('itemDesc').value = item.description;

    modal.style.display = 'flex';
}

// ===== MORPHING AI PANEL =====
function initMorphPanel() {
    const panel = document.getElementById('ai-morph-panel');
    if (!panel) return;

    const toggle = panel.querySelector('.ai-panel-toggle');
    const closeBtn = panel.querySelector('.ai-panel-close');
    const textarea = document.getElementById('ai-panel-textarea');
    const sendBtn = document.getElementById('ai-panel-send');
    const messagesEl = document.getElementById('ai-panel-messages');

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        panel.classList.add('is-open');
        setTimeout(() => textarea && textarea.focus(), 400);
    });

    function closePanel() {
        panel.classList.remove('is-open');
        document.body.style.overflow = '';
    }

    if (closeBtn) closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closePanel();
    });

    document.addEventListener('click', (e) => {
        if (panel.classList.contains('is-open') && !panel.contains(e.target)) {
            closePanel();
        }
    });

    panel.addEventListener('click', (e) => e.stopPropagation());

    if (textarea) {
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closePanel();
                textarea.blur();
            }
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendAiMessage();
            }
        });

        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
        });
    }

    if (sendBtn) sendBtn.addEventListener('click', sendAiMessage);

    async function sendAiMessage() {
        if (!textarea) return;
        const message = textarea.value.trim();
        if (!message) return;

        appendMsg('user', message);
        textarea.value = '';
        textarea.style.height = 'auto';

        const typingEl = document.createElement('div');
        typingEl.className = 'msg-typing';
        typingEl.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
        messagesEl.appendChild(typingEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        try {
            const response = await fetch('/api/chatbot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            const data = await response.json();
            typingEl.remove();

            if (data.response) {
                appendMsg('ai', data.response);
            } else {
                appendMsg('ai', "Sorry, I couldn't process your question. Please try again.");
            }
        } catch (error) {
            typingEl.remove();
            console.error('AI Panel error:', error);
            appendMsg('ai', "I'm having trouble connecting right now. Please try again in a moment.");
        }
    }

    function appendMsg(role, text) {
        const div = document.createElement('div');
        div.className = role === 'user' ? 'msg msg-user' : 'msg msg-ai';
        div.textContent = text;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initMorphPanel();
});
