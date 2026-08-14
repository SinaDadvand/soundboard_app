/**
 * Virtual Soundboard Pro - Frontend Controller
 * ============================================
 * Handles:
 * - Dynamic sound tiles rendering with real-time FX sliders (Volume, Pitch, Speed)
 * - Category/Soundbank filtering & instant search
 * - Interactive 1-click hotkey recorder & backend sync
 * - Audio Device Routing (Primary + Secondary Virtual Cable)
 * - Master Volume, Panic Stop key (`Esc`), and Sound upload
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let sounds = [];
    let categories = ['All'];
    let activeCategory = 'All';
    let currentSearch = '';
    let masterVolume = 1.0;
    let panicKey = 'esc';
    let isRebinding = false;
    let rebindingSoundId = null;
    let activePlayingIds = new Set();

    // DOM Elements
    const grid = document.getElementById('soundboard-grid');
    const emptyState = document.getElementById('empty-state');
    const categoryTabs = document.getElementById('category-tabs-container');
    const searchInput = document.getElementById('sound-search-input');
    const soundCounter = document.getElementById('sound-counter-badge');
    const masterVolSlider = document.getElementById('master-volume-slider');
    const masterVolVal = document.getElementById('master-volume-val');
    const masterMuteBtn = document.getElementById('master-mute-btn');
    const panicStopBtn = document.getElementById('panic-stop-btn');
    const panicKeyBadge = document.getElementById('panic-key-badge');

    // Global FX Elements
    const globalPitchSlider = document.getElementById('global-pitch-slider');
    const globalPitchVal = document.getElementById('global-pitch-val');
    const globalSpeedSlider = document.getElementById('global-speed-slider');
    const globalSpeedVal = document.getElementById('global-speed-val');
    const fxPresetBtns = document.querySelectorAll('.fx-preset-btn');

    // Modals
    const settingsModal = document.getElementById('settings-modal');
    const uploadModal = document.getElementById('upload-modal');
    const rebindModal = document.getElementById('rebind-modal');
    const openSettingsBtn = document.getElementById('open-settings-modal-btn');
    const openUploadBtn = document.getElementById('open-upload-modal-btn');
    const addCategoryBtn = document.getElementById('add-category-btn');

    // Settings Modal Elements
    const primaryDeviceSelect = document.getElementById('primary-device-select');
    const secondaryDeviceSelect = document.getElementById('secondary-device-select');
    const secondaryToggle = document.getElementById('secondary-enabled-toggle');
    const panicKeyInput = document.getElementById('panic-key-input');
    const savePanicKeyBtn = document.getElementById('save-panic-key-btn');
    const saveAudioSettingsBtn = document.getElementById('save-audio-settings-btn');
    const testAudioRoutingBtn = document.getElementById('test-audio-routing-btn');

    // Upload Elements
    const uploadForm = document.getElementById('upload-sound-form');
    const dropzone = document.getElementById('file-dropzone');
    const fileInput = document.getElementById('sound-file-input');
    const fileNameDisplay = document.getElementById('selected-file-name');
    const uploadNameInput = document.getElementById('upload-name-input');
    const uploadCategorySelect = document.getElementById('upload-category-select');
    const uploadHotkeyInput = document.getElementById('upload-hotkey-input');

    // Rebind Modal Elements
    const rebindSoundName = document.getElementById('rebind-sound-name');
    const keyDisplay = document.getElementById('captured-key-display');
    const clearHotkeyBtn = document.getElementById('clear-hotkey-btn');
    const cancelRebindBtn = document.getElementById('cancel-rebind-btn');

    // ─────────────────────────────────────────────────────────────────────────
    // Initialize & Fetch Data
    // ─────────────────────────────────────────────────────────────────────────
    async function init() {
        await loadSounds();
        await loadDevices();
        setupEventListeners();
    }

    async function loadSounds() {
        try {
            const res = await fetch('/api/sounds');
            const data = await res.json();
            sounds = data.sounds || [];
            categories = data.categories || ['All'];
            masterVolume = data.master_volume !== undefined ? data.master_volume : 1.0;
            panicKey = data.panic_key || 'esc';

            masterVolSlider.value = Math.round(masterVolume * 100);
            masterVolVal.textContent = `${masterVolSlider.value}%`;
            panicKeyBadge.textContent = panicKey.toUpperCase();
            panicKeyInput.value = panicKey;

            renderCategories();
            renderSounds();
        } catch (err) {
            console.error('Error loading sounds:', err);
        }
    }

    async function loadDevices() {
        try {
            const res = await fetch('/api/devices');
            const data = await res.json();
            
            primaryDeviceSelect.innerHTML = '<option value="">Default Windows Playback Device</option>';
            secondaryDeviceSelect.innerHTML = '<option value="">Select Virtual Cable...</option>';

            data.devices.forEach(dev => {
                const optPrimary = document.createElement('option');
                optPrimary.value = dev.id;
                optPrimary.textContent = `${dev.name} (${dev.hostapi})`;
                if (dev.id === data.current_primary) optPrimary.selected = true;
                primaryDeviceSelect.appendChild(optPrimary);

                const optSec = document.createElement('option');
                optSec.value = dev.id;
                optSec.textContent = `${dev.name} (${dev.hostapi})`;
                if (dev.id === data.current_secondary) optSec.selected = true;
                secondaryDeviceSelect.appendChild(optSec);
            });

            secondaryToggle.checked = !!data.secondary_enabled;
        } catch (err) {
            console.error('Error loading devices:', err);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Render Functions
    // ─────────────────────────────────────────────────────────────────────────
    function renderCategories() {
        categoryTabs.innerHTML = '';
        const allCats = ['All', ...categories.filter(c => c !== 'All')];

        allCats.forEach(cat => {
            const btn = document.createElement('button');
            const isActive = cat === activeCategory;
            btn.className = `px-3.5 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap ${
                isActive
                    ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-600/20'
                    : 'bg-[#181e2e] text-slate-400 hover:text-white hover:bg-[#232b40]'
            }`;
            btn.textContent = cat;
            btn.addEventListener('click', () => {
                activeCategory = cat;
                renderCategories();
                renderSounds();
            });
            categoryTabs.appendChild(btn);
        });

        // Also update upload category dropdown
        uploadCategorySelect.innerHTML = '';
        categories.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            uploadCategorySelect.appendChild(opt);
        });
    }

    function renderSounds() {
        grid.innerHTML = '';
        
        let filtered = sounds.filter(s => {
            const matchesCat = activeCategory === 'All' || s.category === activeCategory;
            const matchesSearch = currentSearch === '' ||
                s.name.toLowerCase().includes(currentSearch.toLowerCase()) ||
                (s.hotkey && s.hotkey.toLowerCase().includes(currentSearch.toLowerCase()));
            return matchesCat && matchesSearch;
        });

        soundCounter.textContent = `${filtered.length} sounds`;

        if (filtered.length === 0) {
            emptyState.classList.remove('hidden');
            return;
        } else {
            emptyState.classList.add('hidden');
        }

        filtered.forEach(sound => {
            const card = createSoundCard(sound);
            grid.appendChild(card);
        });
    }

    function createSoundCard(sound) {
        const card = document.createElement('div');
        card.id = `card-${sound.id}`;
        card.className = `sound-card p-4 flex flex-col justify-between gap-3 group ${
            activePlayingIds.has(sound.id) ? 'playing' : ''
        }`;

        const isPlaying = activePlayingIds.has(sound.id);
        const hotkeyText = sound.hotkey ? sound.hotkey.toUpperCase() : 'NO KEY';
        const hasHotkey = !!sound.hotkey;

        card.innerHTML = `
            <div>
                <div class="flex items-start justify-between gap-2 mb-1.5">
                    <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-purple-950/60 border border-purple-800/40 text-purple-300">${sound.category || 'All'}</span>
                    <button class="delete-sound-btn text-slate-500 hover:text-red-400 p-1 opacity-0 group-hover:opacity-100 transition" title="Delete sound">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
                <h3 class="font-bold text-slate-100 text-sm leading-snug line-clamp-2">${sound.name}</h3>
            </div>

            <!-- Hotkey Badge & Play Action -->
            <div class="flex items-center justify-between gap-2 pt-1 border-t border-[#232b3d]">
                <button class="hotkey-badge ${hasHotkey ? '' : 'text-slate-500'}" title="Click to rebind hotkey">
                    ${hotkeyText}
                </button>
                <div class="flex items-center gap-1.5">
                    <button class="play-btn p-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-600/30 active:scale-95 transition" title="${isPlaying ? 'Stop' : 'Play'}">
                        ${isPlaying ? `
                            <svg class="w-4 h-4 text-red-300" fill="currentColor" viewBox="0 0 24 24">
                                <rect x="6" y="6" width="12" height="12" rx="2"/>
                            </svg>
                        ` : `
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M8 5v14l11-7z"/>
                            </svg>
                        `}
                    </button>
                </div>
            </div>

            <!-- Quick Inline FX Drawer (Sliders) -->
            <div class="space-y-2 pt-2 border-t border-[#1e2536] text-xs text-slate-400">
                <!-- Volume -->
                <div class="flex items-center justify-between gap-2">
                    <span class="text-[11px] font-semibold">Vol:</span>
                    <input type="range" class="sound-vol-slider w-20 accent-purple-500" min="0" max="1.5" step="0.05" value="${sound.volume !== undefined ? sound.volume : 1.0}">
                    <span class="vol-label font-mono text-[11px] text-purple-300 w-8 text-right">${Math.round((sound.volume !== undefined ? sound.volume : 1.0) * 100)}%</span>
                </div>

                <!-- Pitch & Speed Controls Toggle -->
                <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1">
                        <span class="text-[11px]">FX:</span>
                        <span class="pitch-badge font-mono text-[10px] px-1 rounded bg-[#10141f] text-cyan-400 font-bold">${sound.pitch || 0 > 0 ? '+' : ''}${sound.pitch || 0}st</span>
                        <span class="speed-badge font-mono text-[10px] px-1 rounded bg-[#10141f] text-pink-400 font-bold">${(sound.speed || 1.0).toFixed(1)}x</span>
                    </div>
                    <button class="toggle-fx-btn text-[11px] text-purple-400 hover:underline">Adjust</button>
                </div>

                <!-- Hidden FX Sliders Accordion -->
                <div class="fx-panel hidden space-y-2 pt-2 border-t border-[#181d2a]">
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[10px]">Pitch:</span>
                        <input type="range" class="sound-pitch-slider w-20 accent-cyan-400" min="-12" max="12" step="1" value="${sound.pitch || 0}">
                        <span class="pitch-val font-mono text-[10px] text-cyan-300 w-8 text-right">${sound.pitch || 0}st</span>
                    </div>
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-[10px]">Speed:</span>
                        <input type="range" class="sound-speed-slider w-20 accent-pink-500" min="0.5" max="2.0" step="0.1" value="${sound.speed || 1.0}">
                        <span class="speed-val font-mono text-[10px] text-pink-400 w-8 text-right">${(sound.speed || 1.0).toFixed(1)}x</span>
                    </div>
                </div>
            </div>
        `;

        // Card Event Listeners
        const playBtn = card.querySelector('.play-btn');
        const hotkeyBadge = card.querySelector('.hotkey-badge');
        const deleteBtn = card.querySelector('.delete-sound-btn');
        const volSlider = card.querySelector('.sound-vol-slider');
        const volLabel = card.querySelector('.vol-label');
        const toggleFxBtn = card.querySelector('.toggle-fx-btn');
        const fxPanel = card.querySelector('.fx-panel');
        const pitchSlider = card.querySelector('.sound-pitch-slider');
        const pitchVal = card.querySelector('.pitch-val');
        const speedSlider = card.querySelector('.sound-speed-slider');
        const speedVal = card.querySelector('.speed-val');

        // Play / Stop Trigger
        playBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (activePlayingIds.has(sound.id)) {
                stopSound(sound.id);
            } else {
                playSound(sound);
            }
        });

        // Hotkey Rebind Trigger
        hotkeyBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            openRebindModal(sound);
        });

        // Delete Sound
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (confirm(`Are you sure you want to delete "${sound.name}"?`)) {
                deleteSound(sound.id);
            }
        });

        // Volume slider update
        volSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            sound.volume = val;
            volLabel.textContent = `${Math.round(val * 100)}%`;
            updateSoundConfig(sound.id, { volume: val });
        });

        // Toggle FX drawer
        toggleFxBtn.addEventListener('click', () => {
            fxPanel.classList.toggle('hidden');
        });

        // Pitch slider update
        pitchSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            sound.pitch = val;
            pitchVal.textContent = `${val}st`;
            card.querySelector('.pitch-badge').textContent = `${val > 0 ? '+' : ''}${val}st`;
            updateSoundConfig(sound.id, { pitch: val });
        });

        // Speed slider update
        speedSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            sound.speed = val;
            speedVal.textContent = `${val.toFixed(1)}x`;
            card.querySelector('.speed-badge').textContent = `${val.toFixed(1)}x`;
            updateSoundConfig(sound.id, { speed: val });
        });

        return card;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Sound Playback & Stop Actions
    // ─────────────────────────────────────────────────────────────────────────
    async function playSound(sound) {
        // Calculate global FX + per-sound FX
        const gPitch = parseInt(globalPitchSlider.value) || 0;
        const gSpeed = parseFloat(globalSpeedSlider.value) || 1.0;

        const effectivePitch = (sound.pitch || 0) + gPitch;
        const effectiveSpeed = (sound.speed || 1.0) * gSpeed;
        const effectiveVol = (sound.volume !== undefined ? sound.volume : 1.0);

        // Visual feedback
        activePlayingIds.add(sound.id);
        const card = document.getElementById(`card-${sound.id}`);
        if (card) {
            card.classList.add('playing');
            const playBtn = card.querySelector('.play-btn');
            if (playBtn) {
                playBtn.innerHTML = `
                    <svg class="w-4 h-4 text-red-300" fill="currentColor" viewBox="0 0 24 24">
                        <rect x="6" y="6" width="12" height="12" rx="2"/>
                    </svg>
                `;
            }
        }

        try {
            await fetch(`/api/play/${sound.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    volume: effectiveVol,
                    pitch: effectivePitch,
                    speed: effectiveSpeed
                })
            });
        } catch (err) {
            console.error('Playback error:', err);
        }

        // Auto remove playing state after estimated clip length (or fallback)
        setTimeout(() => {
            activePlayingIds.delete(sound.id);
            if (card) {
                card.classList.remove('playing');
                const playBtn = card.querySelector('.play-btn');
                if (playBtn) {
                    playBtn.innerHTML = `
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    `;
                }
            }
        }, 2000);
    }

    async function stopSound(soundId) {
        activePlayingIds.delete(soundId);
        const card = document.getElementById(`card-${soundId}`);
        if (card) {
            card.classList.remove('playing');
            const playBtn = card.querySelector('.play-btn');
            if (playBtn) {
                playBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                `;
            }
        }
        try {
            await fetch(`/api/sounds/${soundId}/stop`, { method: 'POST' });
        } catch (err) {
            console.error('Stop error:', err);
        }
    }

    async function panicStopAll() {
        activePlayingIds.clear();
        document.querySelectorAll('.sound-card').forEach(c => {
            c.classList.remove('playing');
            const playBtn = c.querySelector('.play-btn');
            if (playBtn) {
                playBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                `;
            }
        });

        try {
            await fetch('/api/stop', { method: 'POST' });
        } catch (err) {
            console.error('Panic stop error:', err);
        }
    }

    async function updateSoundConfig(soundId, updates) {
        try {
            await fetch(`/api/sounds/${soundId}/edit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });
        } catch (err) {
            console.error('Update config error:', err);
        }
    }

    async function deleteSound(soundId) {
        try {
            const res = await fetch(`/api/sounds/${soundId}`, { method: 'DELETE' });
            if (res.ok) {
                sounds = sounds.filter(s => s.id !== soundId);
                renderSounds();
            }
        } catch (err) {
            console.error('Delete sound error:', err);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Rebind Modal / Interactive Key Recorder
    // ─────────────────────────────────────────────────────────────────────────
    function openRebindModal(sound) {
        isRebinding = true;
        rebindingSoundId = sound.id;
        rebindSoundName.textContent = `Clip: ${sound.name}`;
        keyDisplay.textContent = sound.hotkey ? `Current: ${sound.hotkey.toUpperCase()}` : 'Listening for keys...';
        keyDisplay.classList.remove('text-cyan-400');
        keyDisplay.classList.add('text-purple-400');
        rebindModal.classList.remove('hidden');
    }

    function closeRebindModal() {
        isRebinding = false;
        rebindingSoundId = null;
        rebindModal.classList.add('hidden');
    }

    async function finalizeRebind(keyStr) {
        if (!rebindingSoundId) return;
        try {
            const res = await fetch(`/api/sounds/${rebindingSoundId}/rebind`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hotkey: keyStr })
            });
            const data = await res.json();
            if (data.status === 'success') {
                const target = sounds.find(s => s.id === rebindingSoundId);
                if (target) target.hotkey = keyStr;
                renderSounds();
                closeRebindModal();
            } else {
                alert(data.message || 'Error rebinding hotkey');
            }
        } catch (err) {
            console.error('Rebind error:', err);
        }
    }

    // Capture keyboard combination in rebind modal
    window.addEventListener('keydown', (e) => {
        // Global panic key check in browser
        if (e.key.toLowerCase() === panicKey.toLowerCase()) {
            panicStopAll();
            return;
        }

        if (!isRebinding) return;

        e.preventDefault();
        e.stopPropagation();

        const modifiers = [];
        if (e.ctrlKey) modifiers.push('ctrl');
        if (e.altKey) modifiers.push('alt');
        if (e.shiftKey) modifiers.push('shift');

        let key = e.key.toLowerCase();
        // Ignore standalone modifier presses
        if (['control', 'alt', 'shift', 'meta'].includes(key)) {
            keyDisplay.textContent = modifiers.join('+').toUpperCase() + ' + ...';
            return;
        }

        // Clean numpad key representation
        if (e.code.startsWith('Numpad')) {
            key = e.code.replace('Numpad', '').toLowerCase();
        }

        const fullCombo = [...modifiers, key].join('+');
        keyDisplay.textContent = fullCombo.toUpperCase();
        finalizeRebind(fullCombo);
    });

    clearHotkeyBtn.addEventListener('click', () => {
        finalizeRebind(null);
    });

    cancelRebindBtn.addEventListener('click', closeRebindModal);

    // ─────────────────────────────────────────────────────────────────────────
    // Event Listeners & Modals
    // ─────────────────────────────────────────────────────────────────────────
    function setupEventListeners() {
        // Search
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.trim();
            renderSounds();
        });

        // Master Volume
        masterVolSlider.addEventListener('input', async (e) => {
            const val = parseInt(e.target.value) / 100;
            masterVolume = val;
            masterVolVal.textContent = `${e.target.value}%`;
            await fetch('/api/master_volume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volume: val })
            });
        });

        masterMuteBtn.addEventListener('click', async () => {
            if (masterVolume > 0) {
                masterVolSlider.value = 0;
                masterVolume = 0;
            } else {
                masterVolSlider.value = 100;
                masterVolume = 1.0;
            }
            masterVolVal.textContent = `${masterVolSlider.value}%`;
            await fetch('/api/master_volume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volume: masterVolume })
            });
        });

        // Panic Stop Button
        panicStopBtn.addEventListener('click', panicStopAll);

        // Global FX Sliders
        globalPitchSlider.addEventListener('input', (e) => {
            globalPitchVal.textContent = `${e.target.value} st`;
        });

        globalSpeedSlider.addEventListener('input', (e) => {
            globalSpeedVal.textContent = `${parseFloat(e.target.value).toFixed(2)}x`;
        });

        fxPresetBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const pitch = btn.dataset.pitch;
                const speed = btn.dataset.speed;
                globalPitchSlider.value = pitch;
                globalPitchVal.textContent = `${pitch} st`;
                globalSpeedSlider.value = speed;
                globalSpeedVal.textContent = `${parseFloat(speed).toFixed(2)}x`;
            });
        });

        // Settings Modal Open / Close
        openSettingsBtn.addEventListener('click', () => {
            settingsModal.classList.remove('hidden');
        });

        openUploadBtn.addEventListener('click', () => {
            uploadModal.classList.remove('hidden');
        });

        document.querySelectorAll('.close-modal-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                settingsModal.classList.add('hidden');
                uploadModal.classList.add('hidden');
                closeRebindModal();
            });
        });

        // Add Category
        addCategoryBtn.addEventListener('click', async () => {
            const name = prompt('Enter new Soundbank Category name:');
            if (name && name.trim()) {
                const res = await fetch('/api/categories', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name.trim() })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    categories = data.categories;
                    activeCategory = name.trim();
                    renderCategories();
                    renderSounds();
                }
            }
        });

        // Save Audio Routing Settings
        saveAudioSettingsBtn.addEventListener('click', async () => {
            const primary = primaryDeviceSelect.value !== '' ? parseInt(primaryDeviceSelect.value) : null;
            const secondary = secondaryDeviceSelect.value !== '' ? parseInt(secondaryDeviceSelect.value) : null;
            const secondaryEnabled = secondaryToggle.checked;

            try {
                await fetch('/api/devices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        primary_device: primary,
                        secondary_device: secondary,
                        secondary_enabled: secondaryEnabled
                    })
                });
                alert('Audio routing settings saved successfully!');
                settingsModal.classList.add('hidden');
            } catch (err) {
                console.error('Save audio settings error:', err);
            }
        });

        // Save Panic Key
        savePanicKeyBtn.addEventListener('click', async () => {
            const key = panicKeyInput.value.trim().toLowerCase();
            if (key) {
                await fetch('/api/panic_key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ panic_key: key })
                });
                panicKey = key;
                panicKeyBadge.textContent = key.toUpperCase();
                alert(`Panic key updated to [${key.toUpperCase()}]`);
            }
        });

        // Test Audio Routing Chime
        testAudioRoutingBtn.addEventListener('click', async () => {
            if (sounds.length > 0) {
                await playSound(sounds[0]);
            }
        });

        // File Upload Dropzone
        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('border-purple-500', 'bg-purple-950/20');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('border-purple-500', 'bg-purple-950/20');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('border-purple-500', 'bg-purple-950/20');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                handleFileSelected(fileInput.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelected(e.target.files[0]);
            }
        });

        function handleFileSelected(file) {
            fileNameDisplay.textContent = `Selected: ${file.name} (${Math.round(file.size / 1024)} KB)`;
            fileNameDisplay.classList.remove('hidden');
            if (!uploadNameInput.value) {
                uploadNameInput.value = file.name.replace(/\.[^/.]+$/, "");
            }
        }

        // Upload Form Submit
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files || fileInput.files.length === 0) {
                alert('Please select an audio file to upload.');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('name', uploadNameInput.value);
            formData.append('category', uploadCategorySelect.value);
            formData.append('hotkey', uploadHotkeyInput.value);

            try {
                const res = await fetch('/api/sounds/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.status === 'success') {
                    sounds.push(data.sound);
                    renderSounds();
                    uploadModal.classList.add('hidden');
                    uploadForm.reset();
                    fileNameDisplay.classList.add('hidden');
                } else {
                    alert(data.message || 'Upload failed');
                }
            } catch (err) {
                console.error('Upload error:', err);
            }
        });
    }

    // Run
    init();
});
