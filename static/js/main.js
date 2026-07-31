// Shared Frontend Utilities & Shop Selector State Persistence

document.addEventListener('DOMContentLoaded', () => {
    syncActiveShopSelection();
});

// Persistence helper for shop counters
function syncActiveShopSelection() {
    const shopSelect = document.getElementById('active-shop-select');
    if (!shopSelect) return;

    // Load saved shop ID if exists
    const savedShopId = localStorage.getItem('active_shop_id');
    if (savedShopId) {
        // Double check option exists
        const exists = Array.from(shopSelect.options).some(opt => opt.value === savedShopId);
        if (exists) {
            shopSelect.value = savedShopId;
        }
    }

    // Save choice on change
    shopSelect.addEventListener('change', () => {
        localStorage.setItem('active_shop_id', shopSelect.value);
    });
}
