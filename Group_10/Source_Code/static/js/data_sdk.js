window.dataSdk = {
    init: async function(handler) {
        console.log("Data SDK Initialized");
        // This fetches the data from your Flask backend
        try {
            const response = await fetch('/social_skills_api/get_assignments');
            const data = await response.json();
            if (handler && handler.onDataChanged) {
                handler.onDataChanged(data);
            }
            return { isOk: true };
        } catch (e) {
            console.error("Data fetch failed", e);
            return { isOk: false, message: e.message };
        }
    },
    update: async function(record) {
        // This sends updates (like "Session Completed") back to the server
        try {
            const response = await fetch('/social_skills_api/update_assignment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(record)
            });
            return await response.json();
        } catch (e) {
            return { isOk: false, message: e.message };
        }
    }
};