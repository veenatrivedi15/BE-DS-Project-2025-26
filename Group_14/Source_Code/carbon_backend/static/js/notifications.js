// Notification system JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const notificationButton = document.getElementById('notification-button');
    const notificationDropdown = document.getElementById('notification-dropdown');
    const notificationList = document.getElementById('notification-list');
    const notificationBadge = document.getElementById('notification-badge');
    const markAllReadBtn = document.getElementById('mark-all-read-btn');
    
    let notifications = [];
    let unreadCount = 0;
    
    // Toggle notification dropdown
    if (notificationButton && notificationDropdown) {
        notificationButton.addEventListener('click', function(e) {
            e.stopPropagation();
            const isHidden = notificationDropdown.classList.contains('hidden');
            
            if (isHidden) {
                notificationDropdown.classList.remove('hidden');
                loadNotifications();
            } else {
                notificationDropdown.classList.add('hidden');
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!notificationButton.contains(e.target) && !notificationDropdown.contains(e.target)) {
                notificationDropdown.classList.add('hidden');
            }
        });
    }
    
    // Load notifications from API
    function loadNotifications() {
        fetch('/api/notifications/')
            .then(response => response.json())
            .then(data => {
                notifications = data.notifications || [];
                unreadCount = data.unread_count || 0;
                renderNotifications();
                updateBadge();
            })
            .catch(error => {
                console.error('Error loading notifications:', error);
                notificationList.innerHTML = '<div class="p-4 text-center text-red-500">Error loading notifications</div>';
            });
    }
    
    // Render notifications
    function renderNotifications() {
        if (notifications.length === 0) {
            notificationList.innerHTML = '<div class="p-4 text-center text-gray-500">No notifications</div>';
            return;
        }
        
        notificationList.innerHTML = notifications.map(notif => {
            const timeAgo = getTimeAgo(notif.created_at);
            const iconClass = getIconClass(notif.notification_type);
            const bgClass = notif.is_read ? 'bg-white' : 'bg-green-50';
            
            return `
                <div class="p-4 ${bgClass} hover:bg-gray-50 transition-colors" data-notification-id="${notif.id}" data-notification-type="${notif.type}">
                    <div class="flex items-start justify-between">
                        <div class="flex items-start flex-1">
                            <div class="flex-shrink-0">
                                <span class="text-2xl">${iconClass}</span>
                            </div>
                            <div class="ml-3 flex-1">
                                <p class="text-sm font-medium text-gray-900">${escapeHtml(notif.title)}</p>
                                <p class="text-sm text-gray-600 mt-1">${escapeHtml(notif.message)}</p>
                                <p class="text-xs text-gray-400 mt-1">${timeAgo}</p>
                            </div>
                        </div>
                        <div class="flex items-center ml-2">
                            <button class="text-gray-400 hover:text-red-500 delete-notification" data-notification-id="${notif.id}" data-notification-type="${notif.type}" title="Delete">
                                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add event listeners for delete buttons
        document.querySelectorAll('.delete-notification').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const notificationId = this.getAttribute('data-notification-id');
                const notificationType = this.getAttribute('data-notification-type');
                deleteNotification(notificationId, notificationType);
            });
        });
    }
    
    // Update badge
    function updateBadge() {
        if (notificationBadge) {
            if (unreadCount > 0) {
                notificationBadge.style.display = 'block';
                notificationBadge.textContent = unreadCount > 9 ? '9+' : unreadCount;
            } else {
                notificationBadge.style.display = 'none';
            }
        }
    }
    
    // Delete notification
    function deleteNotification(notificationId, notificationType) {
        const formData = new FormData();
        formData.append('type', notificationType);
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
        
        fetch(`/api/notifications/${notificationId}/delete/`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadNotifications();
            }
        })
        .catch(error => {
            console.error('Error deleting notification:', error);
        });
    }
    
    // Mark all as read
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function() {
            fetch('/api/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadNotifications();
                }
            })
            .catch(error => {
                console.error('Error marking all as read:', error);
            });
        });
    }
    
    // Helper functions
    function getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        return date.toLocaleDateString();
    }
    
    function getIconClass(type) {
        const icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'redemption': '💰',
            'trip': '🚗',
            'credit': '💳',
            'system': '🔔',
            'purchase': '🛒',
            'sale': '💵',
            'offer': '📋',
            'status_change': '🔄',
            'other': '📢'
        };
        return icons[type] || '📢';
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Load notifications on page load
    loadNotifications();
    
    // Refresh notifications every 30 seconds
    setInterval(loadNotifications, 30000);
});



