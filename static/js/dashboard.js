// Owner Dashboard Page JavaScript

let dashboardTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initial loads
    loadDashboardData();
    loadCustomerList();

    // Re-load if active shop changes
    const shopSelect = document.getElementById('active-shop-select');
    if (shopSelect) {
        shopSelect.addEventListener('change', () => {
            loadDashboardData();
        });
    }

    // Set polling interval for real-time alerts and counters (every 10 seconds)
    dashboardTimer = setInterval(loadDashboardData, 10000);
});

// Clean timer on navigation if needed (SPA logic)
window.addEventListener('beforeunload', () => {
    if (dashboardTimer) clearInterval(dashboardTimer);
});

// Fetch metrics, charts, and alerts from backend APIs
async function loadDashboardData() {
    const shopSelect = document.getElementById('active-shop-select');
    if (!shopSelect) return;
    const shopId = shopSelect.value;

    try {
        const response = await fetch(`/api/dashboard_data?shop_id=${shopId}`);
        const result = await response.json();

        if (result.success) {
            updateMetricsCards(result.metrics);
            drawChart('weekly-chart', result.weekly_report);
            drawChart('monthly-chart', result.monthly_report);
            renderAlertsList(result.alerts);
        }
    } catch (err) {
        console.error("Dashboard metrics fetch failed:", err);
    }
}

// Update Top Metric Stat counters
function updateMetricsCards(metrics) {
    document.getElementById('stat-todays-customers').innerText = metrics.todays_customers;
    document.getElementById('stat-eligible-count').innerText = metrics.eligible_count;
    document.getElementById('stat-rejected-count').innerText = metrics.rejected_count;
    document.getElementById('stat-total-sold').innerText = `${metrics.total_alcohol_sold} ml`;
}

// Draw custom CSS/SVG bar chart bars
function drawChart(containerId, report) {
    const chartDiv = document.getElementById(containerId);
    if (!chartDiv) return;

    chartDiv.innerHTML = '';
    const maxVal = Math.max(...report.data, 100); // minimum scale boundary

    report.labels.forEach((label, idx) => {
        const val = report.data[idx];
        const pctHeight = (val / maxVal) * 90; // cap at 90% container height

        const barCol = document.createElement('div');
        barCol.className = 'bar-column';
        
        const barFill = document.createElement('div');
        barFill.className = 'bar-fill';
        barFill.setAttribute('data-value', `${val}ml`);
        barFill.style.height = '0%'; // Start at 0% for animation trigger
        
        const barLabel = document.createElement('div');
        barLabel.className = 'bar-label';
        barLabel.innerText = label;

        barCol.appendChild(barFill);
        barCol.appendChild(barLabel);
        chartDiv.appendChild(barCol);

        // Force reflow and animate height
        setTimeout(() => {
            barFill.style.height = `${Math.max(4, pctHeight)}%`; // minimum 4% visual bar
        }, 50);
    });
}

// Populate and style alerts list
function renderAlertsList(alerts) {
    const container = document.getElementById('alerts-container');
    if (!container) return;

    if (alerts.length === 0) {
        container.innerHTML = `
            <p style="color: var(--text-muted); font-size: 0.95rem; text-align: center; padding: 2rem;">
                No suspicious activities detected today.
            </p>
        `;
        return;
    }

    container.innerHTML = '';
    alerts.forEach(alert => {
        const item = document.createElement('div');
        
        // Add alert class mapping
        item.className = `alert-item ${alert.alert_type}`;
        
        // Humanize alert titles
        let title = "Suspicious Event";
        if (alert.alert_type === 'under_18_attempt') title = "Underage Attempt Checked";
        else if (alert.alert_type === 'multiple_purchases_today') title = "Multiple Purchases Today";
        else if (alert.alert_type === 'multi_shop_purchase') title = "Multi-Shop Purchase Attempt";
        else if (alert.alert_type === 'repeated_face_failures') title = "Critical Face Failures";
        else if (alert.alert_type === 'purchase_limit_exceeded') title = "Limit Exceeded Warning";

        item.innerHTML = `
            <div class="alert-header">
                <span class="alert-title">${title}</span>
                <span class="alert-time">${alert.time}</span>
            </div>
            <div class="alert-desc">${alert.description}</div>
            <div class="alert-shop">Shop Location: ${alert.shop_name}</div>
        `;
        container.appendChild(item);
    });
}

// Load registered customers list for lookup dropdown selector
async function loadCustomerList() {
    const select = document.getElementById('history-customer-select');
    if (!select) return;

    try {
        const response = await fetch('/api/customers');
        const customers = await response.json();
        
        // Keep first option
        select.innerHTML = '<option value="">-- Choose registered customer --</option>';
        customers.forEach(cust => {
            const opt = document.createElement('option');
            opt.value = cust.id;
            opt.innerText = `${cust.name} (${cust.id_number})`;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error("Customers list fetch failed:", err);
    }
}

// Fetch ledger details for selected customer
async function loadCustomerHistory() {
    const select = document.getElementById('history-customer-select');
    const detailsCard = document.getElementById('history-details-card');
    const tableBody = document.getElementById('history-table-body');
    const emptyMsg = document.getElementById('history-empty-message');

    if (!select || !select.value) {
        if (detailsCard) detailsCard.style.display = 'none';
        return;
    }

    const customerId = select.value;

    try {
        const response = await fetch(`/api/customer_history/${customerId}`);
        const result = await response.json();

        if (result.success) {
            detailsCard.style.display = 'grid';
            
            // Populate demographics
            document.getElementById('hist-name').innerText = result.customer.name;
            document.getElementById('hist-id').innerText = `${result.customer.id_type}: ${result.customer.id_number}`;
            document.getElementById('hist-dob').innerText = `DOB: ${result.customer.dob}`;
            document.getElementById('hist-photo').src = `/static/${result.customer.photo_path}`;

            // Limits
            const limits = result.limits;
            document.getElementById('hist-weekly-text').innerText = `Remaining: ${limits.remaining_weekly} ml`;
            document.getElementById('hist-monthly-text').innerText = `Remaining: ${limits.remaining_monthly} ml`;

            const weeklyBar = document.getElementById('hist-weekly-bar');
            const monthlyBar = document.getElementById('hist-monthly-bar');
            
            const weeklyPct = (limits.remaining_weekly / limits.weekly_limit) * 100;
            const monthlyPct = (limits.remaining_monthly / limits.monthly_limit) * 100;

            weeklyBar.style.width = `${weeklyPct}%`;
            monthlyBar.style.width = `${monthlyPct}%`;

            // Adjust bar colors
            weeklyBar.className = 'limit-bar-inner';
            if (limits.remaining_weekly <= 50) weeklyBar.classList.add('warning');
            if (limits.remaining_weekly <= 0) weeklyBar.classList.add('danger');

            monthlyBar.className = 'limit-bar-inner';
            if (limits.remaining_monthly <= 200) monthlyBar.classList.add('warning');
            if (limits.remaining_monthly <= 0) monthlyBar.classList.add('danger');

            // Populate ledger transactions
            tableBody.innerHTML = '';
            if (result.history.length === 0) {
                emptyMsg.style.display = 'block';
            } else {
                emptyMsg.style.display = 'none';
                result.history.forEach(tx => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${tx.date}</td>
                        <td>${tx.time}</td>
                        <td>${tx.shop_name}</td>
                        <td style="font-weight: 700; color: var(--secondary);">${tx.quantity} ml</td>
                        <td>${tx.remaining_weekly} ml</td>
                        <td>${tx.remaining_monthly} ml</td>
                    `;
                    tableBody.appendChild(row);
                });
            }
        }
    } catch (err) {
        console.error("Customer ledger fetch failed:", err);
    }
}
