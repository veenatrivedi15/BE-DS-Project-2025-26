window.elementSdk = {
    init: function(handler) {
        console.log("Element SDK Initialized");
        if (handler && handler.onConfigChange) {
            handler.onConfigChange(handler.defaultConfig);
        }
    }
};