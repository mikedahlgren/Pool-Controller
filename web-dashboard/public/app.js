// --- Pump End Time Editing ---
window.editPumpEndTime = function () {
    document.getElementById('pump-end-time-popup').classList.remove('hidden');
    const current = document.getElementById('pump-end-time-tbl').textContent.trim();
    let [time, ampm] = current.split(' ');
    if (time && ampm) {
        let [h, m] = time.split(':');
        h = parseInt(h);
        if (ampm === 'PM' && h !== 12) h += 12;
        if (ampm === 'AM' && h === 12) h = 0;
        document.getElementById('pump-end-time-input').value = `${String(h).padStart(2, '0')}:${m}`;
    }
};
window.closePumpEndTimePopup = function () {
    document.getElementById('pump-end-time-popup').classList.add('hidden');
};
window.savePumpEndTime = async function () {
    if (!pool) return;
    const val = document.getElementById('pump-end-time-input').value;
    try {
        await pool.pump.setPumpEndTime(val);
        showNotification('Pump end time updated', 'success');
        refreshScheduleOverview();
    } catch (e) {
        showNotification('Failed to update pump end time', 'error');
    }
    closePumpEndTimePopup();
};

// --- Schedule Overview Editing ---
let editingScheduleNum = null;

window.editScheduleStart = function (num) {
    editingScheduleNum = num;
    document.getElementById('schedule-time-popup').classList.remove('hidden');
    const current = document.getElementById(`schedule-${num}-start-tbl`).textContent.trim();
    let [time, ampm] = current.split(' ');
    if (time && ampm) {
        let [h, m] = time.split(':');
        h = parseInt(h);
        if (ampm === 'PM' && h !== 12) h += 12;
        if (ampm === 'AM' && h === 12) h = 0;
        document.getElementById('schedule-time-input').value = `${String(h).padStart(2, '0')}:${m}`;
    }
};
window.closeScheduleTimePopup = function () {
    document.getElementById('schedule-time-popup').classList.add('hidden');
    editingScheduleNum = null;
};
window.saveScheduleTime = async function () {
    if (!pool || !editingScheduleNum) return;
    const val = document.getElementById('schedule-time-input').value;
    try {
        await pool.pump.setScheduleStartTime(editingScheduleNum, val);
        showNotification('Start time updated', 'success');
        refreshScheduleOverview();
    } catch (e) {
        showNotification('Failed to update start time', 'error');
    }
    closeScheduleTimePopup();
};

window.editScheduleSpeed = function (num) {
    editingScheduleNum = num;
    document.getElementById('schedule-speed-popup').classList.remove('hidden');
    const current = document.getElementById(`schedule-${num}-speed-tbl`).textContent.trim();
    document.getElementById('schedule-speed-select').value = current;
};
window.closeScheduleSpeedPopup = function () {
    document.getElementById('schedule-speed-popup').classList.add('hidden');
    editingScheduleNum = null;
};
window.saveScheduleSpeed = async function () {
    if (!pool || !editingScheduleNum) return;
    const val = document.getElementById('schedule-speed-select').value;
    try {
        await pool.pump.setScheduleSpeed(editingScheduleNum, val);
        showNotification('Speed updated', 'success');
        refreshScheduleOverview();
    } catch (e) {
        showNotification('Failed to update speed', 'error');
    }
    closeScheduleSpeedPopup();
};

window.toggleScheduleWaterfall = async function (num) {
    if (!pool) return;
    try {
        const current = await pool.pump.getScheduleWaterfall(num);
        const newState = !current;
        await pool.pump.setScheduleWaterfall(num, newState);
        showNotification(`Waterfall ${newState ? 'ON' : 'OFF'}`, 'success');
        refreshScheduleOverview();
    } catch (e) {
        showNotification('Failed to toggle waterfall', 'error');
    }
};

import { createPoolClient } from '../dist/esphome-api.js';

// ===== DRAG AND DROP =====
let draggedCard = null;

function initDragAndDrop() {
    const grid = document.querySelector('.grid');
    if (!grid) return;
    
    const cards = grid.querySelectorAll('.card[draggable="true"]');
    
    cards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
        card.addEventListener('dragover', handleDragOver);
        card.addEventListener('dragenter', handleDragEnter);
        card.addEventListener('dragleave', handleDragLeave);
        card.addEventListener('drop', handleDrop);
    });
    
    // Load saved order
    loadCardOrder();
}

function handleDragStart(e) {
    draggedCard = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', this.dataset.cardId);
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    document.querySelectorAll('.card').forEach(card => {
        card.classList.remove('drag-over');
    });
    draggedCard = null;
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function handleDragEnter(e) {
    e.preventDefault();
    if (this !== draggedCard) {
        this.classList.add('drag-over');
    }
}

function handleDragLeave(e) {
    this.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
    
    if (draggedCard && this !== draggedCard) {
        const grid = document.querySelector('.grid');
        const cards = Array.from(grid.querySelectorAll('.card[draggable="true"]'));
        const draggedIndex = cards.indexOf(draggedCard);
        const targetIndex = cards.indexOf(this);
        
        if (draggedIndex < targetIndex) {
            this.parentNode.insertBefore(draggedCard, this.nextSibling);
        } else {
            this.parentNode.insertBefore(draggedCard, this);
        }
        
        saveCardOrder();
    }
}

function saveCardOrder() {
    const grid = document.querySelector('.grid');
    const cards = grid.querySelectorAll('.card[draggable="true"]');
    const order = Array.from(cards).map(card => card.dataset.cardId);
    localStorage.setItem('cardOrder', JSON.stringify(order));
}

function loadCardOrder() {
    const saved = localStorage.getItem('cardOrder');
    if (!saved) return;
    
    try {
        const order = JSON.parse(saved);
        const grid = document.querySelector('.grid');
        if (!grid) return;
        
        order.forEach(cardId => {
            const card = grid.querySelector(`[data-card-id="${cardId}"]`);
            if (card) {
                grid.appendChild(card);
            }
        });
    } catch (e) {
        console.error('Error loading card order:', e);
    }
}

// Card Width Management
// Width options: narrow (2 cols, 1 internal), default (3 cols, 2 internal), third (4 cols, 2 internal), wide (6 cols, 3 internal)
window.cycleCardWidth = function(button) {
    const card = button.closest('.card');
    if (!card) return;
    
    // Cycle: narrow -> default -> third -> wide -> narrow
    const widthClasses = ['narrow', '', 'third', 'wide'];
    
    let currentIndex = 0;
    if (card.classList.contains('narrow')) currentIndex = 0;
    else if (card.classList.contains('third')) currentIndex = 2;
    else if (card.classList.contains('wide')) currentIndex = 3;
    else currentIndex = 1; // default (no class)
    
    // Cycle to next width
    const nextIndex = (currentIndex + 1) % widthClasses.length;
    
    // Remove all width classes
    card.classList.remove('narrow', 'third', 'wide', 'single');
    
    // Add new width class if not default
    if (widthClasses[nextIndex]) {
        card.classList.add(widthClasses[nextIndex]);
    }
    
    saveCardWidths();
};

function saveCardWidths() {
    const cards = document.querySelectorAll('.card[data-card-id]');
    const widths = {};
    
    cards.forEach(card => {
        const id = card.dataset.cardId;
        if (card.classList.contains('single')) widths[id] = 'single';
        else if (card.classList.contains('narrow')) widths[id] = 'narrow';
        else if (card.classList.contains('third')) widths[id] = 'third';
        else if (card.classList.contains('wide')) widths[id] = 'wide';
        else widths[id] = 'default';
    });
    
    localStorage.setItem('cardWidths', JSON.stringify(widths));
}

function loadCardWidths() {
    const saved = localStorage.getItem('cardWidths');
    if (!saved) return;
    
    try {
        const widths = JSON.parse(saved);
        Object.keys(widths).forEach(cardId => {
            const card = document.querySelector(`[data-card-id="${cardId}"]`);
            if (card && widths[cardId] !== 'default') {
                card.classList.remove('narrow', 'third', 'wide', 'single');
                card.classList.add(widths[cardId]);
            }
        });
    } catch (e) {
        console.error('Error loading card widths:', e);
    }
}

// Reset all stored settings and reload
window.resetAllSettings = function() {
    if (confirm('This will reset all settings, card positions, card widths, and dark mode preference. Are you sure?')) {
        localStorage.removeItem('poolSettings');
        localStorage.removeItem('cardOrder');
        localStorage.removeItem('cardWidths');
        localStorage.removeItem('darkMode');
        showNotification('All settings reset. Reloading...', 'success');
        setTimeout(() => window.location.reload(), 1000);
    }
};

let pool = null;
let autoRefreshInterval = null;

// Load saved settings from localStorage
function loadSettings() {
    const saved = localStorage.getItem('poolSettings');
    if (saved) {
        try {
            const settings = JSON.parse(saved);
            const hostEl = document.getElementById('host');
            const portEl = document.getElementById('port');
            const usernameEl = document.getElementById('username');
            const passwordEl = document.getElementById('password');
            const autoRefreshEl = document.getElementById('auto-refresh-toggle');
            const refreshIntervalEl = document.getElementById('refresh-interval');
            
            if (hostEl && settings.host) hostEl.value = settings.host;
            if (portEl && settings.port) portEl.value = settings.port;
            if (usernameEl && settings.username) usernameEl.value = settings.username;
            if (passwordEl && settings.password) passwordEl.value = settings.password;
            if (autoRefreshEl && settings.autoRefresh !== undefined) {
                autoRefreshEl.checked = settings.autoRefresh;
            }
            if (refreshIntervalEl && settings.refreshInterval) {
                refreshIntervalEl.value = settings.refreshInterval;
            }
            return settings;
        } catch (e) {
            console.error('Error loading settings:', e);
        }
    }
    updateRefreshButtonVisibility();
    return null;
}

// Save settings to localStorage
function saveSettings() {
    const settings = {
        host: document.getElementById('host').value,
        port: document.getElementById('port').value,
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
        autoRefresh: document.getElementById('auto-refresh-toggle').checked,
        refreshInterval: document.getElementById('refresh-interval').value
    };
    localStorage.setItem('poolSettings', JSON.stringify(settings));
}

// Show/hide refresh button based on auto-refresh state
function updateRefreshButtonVisibility() {
    const autoRefreshOn = document.getElementById('auto-refresh-toggle')?.checked;
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.style.display = autoRefreshOn ? 'none' : 'flex';
    }
}

// Initialize chlorine slider
document.getElementById('chlorine-slider')?.addEventListener('input', (e) => {
    document.getElementById('chlorine-value').textContent = e.target.value;
});

// Connect to ESPHome device
window.connectToDevice = async function () {
    const currentHost = window.location.hostname;
    const needsProxy = currentHost === 'localhost' || currentHost === '127.0.0.1' || currentHost === '';

    try {
        const host = document.getElementById('host').value.trim();
        const port = document.getElementById('port').value.trim();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();

        pool = createPoolClient({
            host: host,
            port: parseInt(port) || 80,
            username: username || undefined,
            password: password || undefined,
            useProxy: needsProxy,
        });

        await pool.pump.getPumpRunning();

        const connStatus = document.getElementById('connection-status');
        connStatus.innerHTML = '<i class="mdi mdi-check-circle"></i> Online';
        connStatus.className = 'conn-badge online';
        document.getElementById('connect-btn').disabled = true;
        document.getElementById('disconnect-btn').disabled = false;

        document.getElementById('offline-state').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        document.getElementById('settings-overlay').classList.add('hidden');

        await refreshAll();
        showNotification('Connected successfully!', 'success');
        
        // Save settings
        saveSettings();
        
        // Start auto-refresh if enabled
        if (document.getElementById('auto-refresh-toggle')?.checked) {
            const interval = parseInt(document.getElementById('refresh-interval').value) * 1000;
            autoRefreshInterval = setInterval(refreshAll, interval);
        }
        updateRefreshButtonVisibility();
    } catch (error) {
        console.error('Connection error:', error);
        showNotification('Connection failed: ' + error.message, 'error');
    }
};

window.disconnectFromDevice = function () {
    pool = null;
    const connStatus = document.getElementById('connection-status');
    connStatus.innerHTML = '<i class="mdi mdi-wifi-off"></i> Offline';
    connStatus.className = 'conn-badge offline';
    document.getElementById('connect-btn').disabled = false;
    document.getElementById('disconnect-btn').disabled = true;

    document.getElementById('offline-state').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');

    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        const toggle = document.getElementById('auto-refresh-toggle');
        if (toggle) toggle.checked = false;
    }

    showNotification('Disconnected', 'info');
};

window.toggleSettings = function () {
    const overlay = document.getElementById('settings-overlay');
    overlay.classList.toggle('hidden');
};

async function refreshAll() {
    await Promise.all([
        refreshSystemInfo(),
        refreshPumpStatus(),
        refreshTemperatures(),
        refreshAlarms(),
        refreshChlorinator(),
        refreshPumpMode(),
        refreshPumpSpeeds(),
        refreshPoolLight(),
        refreshSwitches(),
        refreshScheduleOverview(),
        refreshFilterPressure()
    ]);
}
window.refreshAll = refreshAll;

window.refreshSystemInfo = async function () {
    if (!pool) return;
    try {
        const info = await pool.system.getSystemInfo();
        document.getElementById('esphome-version').textContent = info.esphomeVersion;
        document.getElementById('wifi-ssid').textContent = info.ssid;
        document.getElementById('wifi-ip').textContent = info.ipAddress;
        document.getElementById('wifi-signal').textContent = `${info.wifiSignal} dBm`;
    } catch (error) {
        console.error('Error refreshing system info:', error);
    }
};

window.refreshPumpStatus = async function () {
    if (!pool) return;
    try {
        const pumpRunning = await pool.pump.getPumpRunning();
        updateStatusBadge('pump-running', pumpRunning);
        updateQuickControl('qc-pump', pumpRunning);

        const pumpStatus = await pool.pump.getPumpStatus();
        updateStatusBadge('pump-status', pumpStatus);

        const metrics = await pool.pump.getPumpMetrics();
        document.getElementById('pump-rpm').textContent = metrics.pumpRpm ?? '--';
        document.getElementById('pump-power').textContent = metrics.power ?? '--';
        document.getElementById('pump-flow').textContent = metrics.flowM3H ?? '--';
        document.getElementById('pump-pressure').textContent = metrics.pressure ? metrics.pressure.toFixed(2) + ' bar' : 'N/A';
        document.getElementById('time-remaining').textContent = metrics.timeRemaining ?? '--';
        
        const pumpStat = document.getElementById('pump-stat');
        if (pumpStat) pumpStat.classList.toggle('running', pumpRunning);

        try {
            const program = await pool.pump.getPumpProgram();
            document.getElementById('pump-program').textContent = program || 'None';
        } catch (e) {
            document.getElementById('pump-program').textContent = 'N/A';
        }

        const clockFormatted = await pool.pump.getPumpClockFormatted();
        document.getElementById('pump-clock-formatted').textContent = clockFormatted;

        const currentSchedule = await pool.pump.getCurrentSchedule();
        document.getElementById('current-schedule').textContent = currentSchedule;
    } catch (error) {
        console.error('Error refreshing pump status:', error);
    }
};

window.refreshTemperatures = async function () {
    if (!pool) return;
    try {
        const temps = await pool.temperature.getTemperatures();
        document.getElementById('air-temp-f').textContent = temps.airTemperatureF;
        document.getElementById('pool-temp-f').textContent = temps.waterTemperatureF;

        try {
            const chlorinatorMetrics = await pool.chlorinator.getChlorinatorMetrics();
            document.getElementById('solar-temp-f').textContent = chlorinatorMetrics.chlorinatorTemperature;
        } catch (e) {
            document.getElementById('solar-temp-f').textContent = 'N/A';
        }
    } catch (error) {
        console.error('Error refreshing temperatures:', error);
    }
};

window.refreshAlarms = async function () {
    if (!pool) return;
    const activeAlarms = [];
    try {
        const alarms = await pool.chlorinator.getChlorinatorAlarms();
        updateAlarm('alarm-no-flow', alarms.noFlowAlarm);
        updateAlarm('alarm-low-salt', alarms.lowSaltAlarm);
        updateAlarm('alarm-high-salt', alarms.highSaltAlarm);
        updateAlarm('alarm-clean-cell', alarms.cleanCellRequired);
        updateAlarm('alarm-high-current', alarms.highCurrentAlarm);
        updateAlarm('alarm-low-voltage', alarms.lowVoltageAlarm);
        updateAlarm('alarm-low-temp', alarms.lowTemperatureAlarm);
        updateAlarm('alarm-check-pcb', alarms.checkPcb);

        if (alarms.noFlowAlarm === true || alarms.noFlowAlarm === 'ON') activeAlarms.push('No Flow');
        if (alarms.lowSaltAlarm === true || alarms.lowSaltAlarm === 'ON') activeAlarms.push('Low Salt');
        if (alarms.highSaltAlarm === true || alarms.highSaltAlarm === 'ON') activeAlarms.push('High Salt');
        if (alarms.cleanCellRequired === true || alarms.cleanCellRequired === 'ON') activeAlarms.push('Clean Cell');
        if (alarms.highCurrentAlarm === true || alarms.highCurrentAlarm === 'ON') activeAlarms.push('High Current');
        if (alarms.lowVoltageAlarm === true || alarms.lowVoltageAlarm === 'ON') activeAlarms.push('Low Voltage');
        if (alarms.lowTemperatureAlarm === true || alarms.lowTemperatureAlarm === 'ON') activeAlarms.push('Low Temp');
        if (alarms.checkPcb === true || alarms.checkPcb === 'ON') activeAlarms.push('Check PCB');
    } catch (error) {
        console.log('Chlorinator not available:', error.message);
    }

    try {
        const filter = await pool.filter.getStatus();
        updateAlarm('alarm-filter-backwash', filter.needsBackwash);
        updateAlarm('alarm-filter-fault', filter.fault);
        if (filter.needsBackwash === true || filter.needsBackwash === 'ON') activeAlarms.push('Filter Backwash');
        if (filter.fault === true || filter.fault === 'ON') activeAlarms.push('Filter Sensor Fault');
    } catch (error) {
        console.log('Filter pressure not available:', error.message);
    }

    const banner = document.getElementById('alarm-banner');
    if (banner) {
        banner.classList.toggle('hidden', activeAlarms.length === 0);
        if (activeAlarms.length > 0) {
            document.getElementById('alarm-message').textContent = activeAlarms.join(', ');
        }
    }
};

window.refreshFilterPressure = async function () {
    if (!pool) return;
    try {
        const filter = await pool.filter.getStatus();
        const psiText = Number.isFinite(filter.pressurePsi) ? filter.pressurePsi.toFixed(1) : '--';
        document.getElementById('filter-psi').textContent = psiText;
        document.getElementById('filter-pressure-psi').textContent = Number.isFinite(filter.pressurePsi) ? `${filter.pressurePsi.toFixed(1)} psi` : 'N/A';
        document.getElementById('filter-pressure-bar').textContent = Number.isFinite(filter.pressureBar) ? `${filter.pressureBar.toFixed(2)} bar` : 'N/A';
        document.getElementById('filter-loop-ma').textContent = Number.isFinite(filter.loopCurrentMa) ? `${filter.loopCurrentMa.toFixed(2)} mA` : 'N/A';
        document.getElementById('filter-clean-psi').textContent = Number.isFinite(filter.cleanPsi) ? `${filter.cleanPsi.toFixed(1)} psi` : '-';
        document.getElementById('filter-rise-psi').textContent = Number.isFinite(filter.risePsi) ? `${filter.risePsi.toFixed(1)} psi` : '-';
        updateStatusBadge('filter-backwash', filter.needsBackwash);
        const filterStat = document.getElementById('filter-stat');
        if (filterStat) filterStat.classList.toggle('warn', !!(filter.needsBackwash || filter.fault));
    } catch (error) {
        console.log('Filter pressure not available:', error.message);
        document.getElementById('filter-psi').textContent = 'N/A';
        document.getElementById('filter-pressure-psi').textContent = 'N/A';
        document.getElementById('filter-pressure-bar').textContent = 'N/A';
        document.getElementById('filter-loop-ma').textContent = 'N/A';
    }
};

window.saveCleanFilterPressure = async function () {
    if (!pool) return;
    try {
        await pool.filter.saveCleanPressure();
        showNotification('Clean filter pressure saved', 'success');
        await refreshFilterPressure();
    } catch (error) {
        console.error('Error saving clean filter pressure:', error);
        showNotification('Failed to save clean pressure', 'error');
    }
};

window.refreshChlorinator = async function () {
    if (!pool) return;
    try {
        const metrics = await pool.chlorinator.getChlorinatorMetrics();
        document.getElementById('salt-level').textContent = metrics.saltLevel ?? 'N/A';
        document.getElementById('chlor-temp').textContent = metrics.chlorinatorTemperature ? metrics.chlorinatorTemperature + '°' : 'N/A';
        document.getElementById('chlorinator-status').textContent = metrics.chlorinatorStatus ?? 'N/A';
        document.getElementById('chlorinator-error').textContent = metrics.chlorinatorError ?? 'N/A';
        document.getElementById('chlorinator-output').textContent = metrics.chlorinatorOutput ?? 'N/A';

        const version = await pool.chlorinator.getChlorinatorVersion();
        document.getElementById('chlorinator-version').textContent = version;

        const output = await pool.chlorinator.getChlorineOutputSetting();
        document.getElementById('chlorine-slider').value = output;
        document.getElementById('chlorine-value').textContent = output;
    } catch (error) {
        console.log('Chlorinator not available:', error.message);
        document.getElementById('salt-level').textContent = 'N/A';
        document.getElementById('chlor-temp').textContent = 'N/A';
        document.getElementById('chlorinator-status').textContent = 'N/A';
        document.getElementById('chlorinator-error').textContent = 'N/A';
        document.getElementById('chlorinator-output').textContent = 'N/A';
        document.getElementById('chlorinator-version').textContent = 'N/A';
    }
};

window.refreshPumpMode = async function () {
    if (!pool) return;
    try {
        const mode = await pool.pump.getMode();
        document.getElementById('current-mode').textContent = mode;
        document.getElementById('mode-select').value = mode;
    } catch (error) {
        console.error('Error refreshing pump mode:', error);
    }
};

window.refreshPumpSpeeds = async function () {
    if (!pool) return;
    try {
        for (let i = 1; i <= 5; i++) {
            const speed = await pool.pump.getPumpSpeed(i);
            document.getElementById(`speed-${i}`).value = speed;
        }
    } catch (error) {
        console.error('Error refreshing pump speeds:', error);
    }
};

window.refreshPoolLight = async function () {
    if (!pool) return;
    try {
        const poolLight = await pool.light.getPoolLightState();
        const btn = document.getElementById('switch-pool-light');
        const isOn = poolLight === true || poolLight === 'ON';
        btn.textContent = isOn ? 'ON' : 'OFF';
        btn.className = 'tog-btn ' + (isOn ? 'on' : 'off');
        updateQuickControl('qc-light', isOn);

        try {
            const mode = await pool.light.getLightMode();
            document.getElementById('light-mode-select').value = mode;
            document.getElementById('current-light-mode').textContent = mode;
        } catch (modeError) {
            console.log('Light mode not available:', modeError.message);
        }
    } catch (error) {
        console.error('Error refreshing pool light:', error);
    }
};

window.refreshSwitches = async function () {
    if (!pool) return;
    try {
        const waterfall = await pool.pump.getWaterfall();
        updateToggleButton('switch-waterfall', waterfall);
        updateQuickControl('qc-waterfall', waterfall);

        const waterfallAuto = await pool.pump.getWaterfallAuto();
        updateToggleButton('switch-waterfall-auto', waterfallAuto);

        const autoSchedule = await pool.pump.getAutoSchedule();
        updateToggleButton('switch-auto-schedule', autoSchedule);
        updateQuickControl('qc-schedule', autoSchedule);

        const takeover = await pool.pump.getTakeoverMode();
        updateToggleButton('switch-takeover', takeover);

        const off = await pool.pump.getOff();
        updateToggleButton('switch-off', off);

        const lightMode = await pool.light.getLightMode();
        document.getElementById('current-light-mode').textContent = lightMode;
        document.getElementById('light-mode-select').value = lightMode;
    } catch (error) {
        console.error('Error refreshing switches:', error);
    }
};

window.refreshScheduleOverview = async function () {
    if (!pool) return;
    try {
        const convertTo12Hour = (time24) => {
            const [hours, minutes] = time24.split(':');
            let h = parseInt(hours);
            const ampm = h >= 12 ? 'PM' : 'AM';
            h = h % 12 || 12;
            return `${h}:${minutes} ${ampm}`;
        };

        const scheduleStatuses = await pool.pump.getScheduleStatuses();
        const scheduleRpms = await pool.pump.getScheduleRpms();

        for (let i = 1; i <= 5; i++) {
            const statusKey = `schedule${i}Status`;
            const statusText = scheduleStatuses[statusKey] ?? '';
            document.getElementById(`schedule-${i}-status-tbl`).textContent = statusText;

            const startTime = await pool.pump.getScheduleStartTime(i);
            document.getElementById(`schedule-${i}-start-tbl`).textContent = convertTo12Hour(startTime.substring(0, 5));

            const speed = await pool.pump.getScheduleSpeed(i);
            document.getElementById(`schedule-${i}-speed-tbl`).textContent = speed;

            const rpmKey = `schedule${i}Rpm`;
            document.getElementById(`schedule-${i}-rpm-tbl`).textContent = scheduleRpms[rpmKey] || '0';

            const waterfall = await pool.pump.getScheduleWaterfall(i);
            const waterfallSpan = document.getElementById(`schedule-${i}-waterfall-tbl`);
            const isOn = waterfall === true || waterfall === 'ON';
            waterfallSpan.textContent = isOn ? 'ON' : 'OFF';
            waterfallSpan.className = 'wf-badge ' + (isOn ? 'on' : 'off');
        }

        const scheduleOffStatus = await pool.pump.getScheduleOffStatus();
        document.getElementById('schedule-off-status-tbl').textContent = scheduleOffStatus;

        const pumpEndTime = await pool.pump.getPumpEndTime();
        document.getElementById('pump-end-time-tbl').textContent = convertTo12Hour(pumpEndTime.substring(0, 5));
    } catch (error) {
        console.error('Error refreshing schedule overview:', error);
    }
};

window.setChlorineOutput = async function () {
    if (!pool) return;
    try {
        const value = parseInt(document.getElementById('chlorine-slider').value);
        await pool.chlorinator.setChlorineOutput(value);
        showNotification(`Chlorine output set to ${value}%`, 'success');
        await refreshChlorinator();
    } catch (error) {
        console.error('Error setting chlorine output:', error);
        showNotification('Error setting chlorine output', 'error');
    }
};

window.setPumpMode = async function () {
    if (!pool) return;
    try {
        const mode = document.getElementById('mode-select').value;
        await pool.pump.setMode(mode);
        showNotification(`Pump mode set to ${mode}`, 'success');
        await refreshPumpMode();
    } catch (error) {
        console.error('Error setting pump mode:', error);
        showNotification('Error setting pump mode', 'error');
    }
};

window.setPumpSpeed = async function (speedNum) {
    if (!pool) return;
    try {
        const rpm = parseInt(document.getElementById(`speed-${speedNum}`).value);
        await pool.pump.setPumpSpeed(speedNum, rpm);
        showNotification(`Pump Speed ${speedNum} set to ${rpm} RPM`, 'success');
    } catch (error) {
        console.error('Error setting pump speed:', error);
        showNotification('Error setting pump speed', 'error');
    }
};

window.adjustSpeed = function (speedNum, delta) {
    const input = document.getElementById(`speed-${speedNum}`);
    let currentValue = parseInt(input.value) || 450;
    let newValue = currentValue + delta;
    const min = parseInt(input.min) || 450;
    const max = parseInt(input.max) || 3450;
    newValue = Math.max(min, Math.min(max, newValue));
    input.value = newValue;
};

window.toggleSwitch = async function (switchId, button) {
    if (!pool) return;
    try {
        if (switchId === 'waterfall') {
            await pool.pump.toggleWaterfall();
            const state = await pool.pump.getWaterfall();
            updateToggleButton(button.id, state);
            updateQuickControl('qc-waterfall', state);
            showNotification(`Waterfall toggled ${state ? 'ON' : 'OFF'}`, 'success');
        } else if (switchId === 'pool_light') {
            await pool.light.togglePoolLight();
            const state = await pool.light.getPoolLightState();
            updateToggleButton(button.id, state);
            updateQuickControl('qc-light', state);
            showNotification(`Pool light toggled ${state ? 'ON' : 'OFF'}`, 'success');
        } else if (switchId === 'takeover_mode') {
            await pool.pump.toggleTakeoverMode();
            const state = await pool.pump.getTakeoverMode();
            updateToggleButton(button.id, state);
            showNotification(`Takeover mode toggled ${state ? 'ON' : 'OFF'}`, 'success');
        } else if (switchId === 'waterfall__auto_') {
            await pool.pump.toggleWaterfallAuto();
            const state = await pool.pump.getWaterfallAuto();
            updateToggleButton(button.id, state);
            showNotification(`Waterfall auto mode toggled ${state ? 'ON' : 'OFF'}`, 'success');
        } else if (switchId === 'auto_schedule') {
            await pool.pump.toggleAutoSchedule();
            const state = await pool.pump.getAutoSchedule();
            updateToggleButton(button.id, state);
            updateQuickControl('qc-schedule', state);
            showNotification(`Auto schedule toggled ${state ? 'ON' : 'OFF'}`, 'success');
        } else if (switchId === 'off') {
            await pool.pump.toggleOff();
            const state = await pool.pump.getOff();
            updateToggleButton(button.id, state);
            showNotification(`System OFF toggled ${state ? 'ON' : 'OFF'}`, 'success');
        } else {
            showNotification(`Switch ${switchId} not yet implemented`, 'warning');
        }
    } catch (error) {
        console.error('Error toggling switch:', error);
        showNotification('Error toggling switch', 'error');
    }
};

window.toggleQuickPump = async function () {
    if (!pool) return;
    try {
        const running = await pool.pump.getPumpRunning();
        if (running) {
            await pool.pump.stopPump();
            showNotification('Pump stopped', 'success');
        } else {
            await pool.pump.runPump();
            showNotification('Pump started', 'success');
        }
        setTimeout(() => refreshPumpStatus(), 1000);
    } catch (error) {
        console.error('Error toggling pump:', error);
        showNotification('Error toggling pump', 'error');
    }
};

window.setLightMode = async function () {
    if (!pool) return;
    const mode = document.getElementById('light-mode-select').value;
    if (!mode) return;
    try {
        await pool.light.setLightMode(mode);
        showNotification(`Light mode set to ${mode}`, 'success');
        await refreshSwitches();
    } catch (error) {
        console.error('Error setting light mode:', error);
        showNotification('Error setting light mode', 'error');
    }
};

window.refreshChlorinatorAction = async function () {
    if (!pool) return;
    try {
        await pool.chlorinator.refreshChlorinator();
        showNotification('Chlorinator refreshed', 'success');
        await refreshChlorinator();
    } catch (error) {
        console.error('Error refreshing chlorinator:', error);
        showNotification('Error refreshing chlorinator', 'error');
    }
};

window.toggleAutoRefresh = function () {
    const enabled = document.getElementById('auto-refresh-toggle').checked;
    const interval = parseInt(document.getElementById('refresh-interval').value) * 1000;

    if (enabled) {
        autoRefreshInterval = setInterval(refreshAll, interval);
        showNotification('Auto-refresh enabled', 'success');
    } else {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        showNotification('Auto-refresh disabled', 'info');
    }
    saveSettings();
    updateRefreshButtonVisibility();
};

window.dismissAlarm = function () {
    document.getElementById('alarm-banner')?.classList.add('hidden');
};

// Helper Functions
function updateStatusBadge(elementId, state) {
    const element = document.getElementById(elementId);
    if (!element) return;
    const isOn = state === true || state === 'ON' || state === 'on';
    element.textContent = isOn ? 'ON' : 'OFF';
    element.className = 'pill ' + (isOn ? 'on' : 'off');
}

function updateAlarm(elementId, active) {
    const element = document.getElementById(elementId);
    if (!element) return;
    const isActive = active === true || active === 'ON' || active === 'on';
    element.classList.toggle('active', isActive);
}

function updateToggleButton(elementId, state) {
    const button = document.getElementById(elementId);
    if (!button) return;
    const isOn = state === true || state === 'ON' || state === 'on';
    button.textContent = isOn ? 'ON' : 'OFF';
    button.className = 'tog-btn ' + (isOn ? 'on' : 'off');
}

function updateQuickControl(elementId, state) {
    const qc = document.getElementById(elementId);
    if (!qc) return;
    const isOn = state === true || state === 'ON' || state === 'on';
    qc.classList.toggle('active', isOn);
    const statusSpan = document.getElementById(elementId + '-status');
    if (statusSpan) statusSpan.textContent = isOn ? 'ON' : 'OFF';
}

function showNotification(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'mdi-check-circle' : type === 'error' ? 'mdi-alert-circle' : type === 'warning' ? 'mdi-alert' : 'mdi-information';
    toast.innerHTML = `<i class="mdi ${icon}"></i><span>${message}</span><button class="toast-close" onclick="this.parentElement.remove()"><i class="mdi mdi-close"></i></button>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 200);
    }, 4000);
}

// Auto-connect
async function checkAndAutoConnect() {
    const savedSettings = loadSettings();
    const currentHost = window.location.hostname;
    
    // Use saved host or current host
    const hostToUse = savedSettings?.host || currentHost;
    const portToUse = savedSettings?.port || 80;
    
    // Update host field if no saved settings
    const hostEl = document.getElementById('host');
    if (hostEl && !savedSettings?.host) hostEl.value = currentHost;

    // Skip auto-connect if on localhost/development server and no saved settings
    if ((currentHost === 'localhost' || currentHost === '127.0.0.1' || currentHost === '') && !savedSettings?.host) {
        console.log('Development mode - opening settings');
        document.getElementById('settings-overlay').classList.remove('hidden');
        return;
    }

    try {
        const testClient = createPoolClient({
            host: hostToUse,
            port: parseInt(portToUse) || 80,
            useProxy: currentHost === 'localhost' || currentHost === '127.0.0.1' || currentHost === ''
        });
        await testClient.pump.getPumpRunning();
        await connectToDevice();
        console.log('Auto-connected to API');
    } catch (error) {
        // API not available - open settings
        console.log('Auto-connect failed, opening settings');
        document.getElementById('settings-overlay').classList.remove('hidden');
    }
}

// Event Listeners
document.getElementById('connect-btn')?.addEventListener('click', connectToDevice);
document.getElementById('disconnect-btn')?.addEventListener('click', disconnectFromDevice);

// Dark Mode
window.toggleDarkMode = function () {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
};

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    // Dark mode
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.body.classList.add('dark-mode');
    }
    // Initialize drag and drop
    initDragAndDrop();
    // Load card widths
    loadCardWidths();
    // Auto-connect (also loads settings)
    checkAndAutoConnect();
});
