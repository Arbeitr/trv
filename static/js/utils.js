/**
 * Shared Utility Functions
 */

const Utils = (function() {
    /**
     * Format travel time in minutes to human-readable string
     * @param {number} minutes - Travel time in minutes
     * @returns {string} Formatted time like "2h 30m" or "45 min"
     */
    function formatTravelTime(minutes) {
        const hours = Math.floor(minutes / 60);
        const remaining_minutes = minutes % 60;
        if (hours > 0) {
            return `${hours}h ${remaining_minutes}m`;
        } else {
            return `${remaining_minutes} min`;
        }
    }
    
    // Public API
    return {
        formatTravelTime
    };
})();
