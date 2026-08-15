/**
 * Virtual Soundboard Numpad Pro - Frontend Controller
 * ==================================================
 * - 3 Numpad Keycap Sections (Ctrl, Alt, Ctrl+Alt)
 * - Gold Rotary Volume Knob with drag & scroll support
 * - Browser Click Playback uses Global FX; Physical Hotkeys use per-clip FX
 * - Individual Reset (↺) buttons on every Pitch, Speed, and Volume slider
 * - High-contrast visible slider tracks
 * - Audio device routing to VB-CABLE Input for OBS / Discord streaming
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let sounds = [];
    let masterVolume = 1.0;
    let panicKey = 'esc';
    let isRebinding = false;
    let rebindingSoundId = null;
    let activePlayingIds = new Set();

    // DOM Grids
    const gridCtrl = document.getElementById('grid-ctrl');
    const gridAlt = document.getElementById('grid-alt');
    const gridCtrlAlt = document.getElementById('grid-ctrl-alt');
    const soundCounter = document.getElementById('sound-counter-badge');

    // Rotary Knob Elements
    const volumeKnob = document.getElementById('volume-knob');
    const knobIndicator = document.getElementById('knob-indicator');
    const masterVolVal = document.getElementById('master-volume-val');
    const masterMuteBtn = document.getElementById('master-mute-btn');
    const panicStopBtn = document.getElementById('panic-stop-btn');
    const panicKeyBadge = document.getElementById('panic-key-badge');

    // Global FX Elements
    const globalPitchSlider = document.getElementById('global-pitch-slider');
    const globalPitchVal = document.getElementById('global-pitch-val');
    const resetGlobalPitchBtn = document.getElementById('reset-global-pitch-btn');
    const globalSpeedSlider = document.getElementById('global-speed-slider');
    const globalSpeedVal = document.getElementById('global-speed-val');
    const resetGlobalSpeedBtn = document.getElementById('reset-global-speed-btn');
    const fxPresetBtns = document.querySelectorAll('.fx-preset-btn');

    // Modals
    const settingsModal = document.getElementById('settings-modal');
    const uploadModal = document.getElementById('upload-modal');
    const rebindModal = document.getElementById('rebind-modal');
    const openSettingsBtn = document.getElementById('open-settings-modal-btn');
    const openUploadBtn = document.getElementById('open-upload-modal-btn');

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
    const uploadHotkeyInput = document.getElementById('upload-hotkey-input');

    // Rebind Modal Elements
    const rebindSoundName = document.getElementById('rebind-sound-name');
    const keyDisplay = document.getElementById('captured-key-display');
    const clearHotkeyBtn = document.getElementById('clear-hotkey-btn');
    const cancelRebindBtn = document.getElementById('cancel-rebind-btn');

    // ─────────────────────────────────────────────────────────────────────────
    // Init & Data Loading
    // ─────────────────────────────────────────────────────────────────────────
    async function init() {
        await loadSounds();
        await loadDevices();
        setupEventListeners();
        setupRotaryKnob();
    }

    async function loadSounds() {
        try {
            const res = await fetch('/api/sounds');
            const data = await res.json();
            sounds = data.sounds || [];
            masterVolume = data.master_volume !== undefined ? data.master_volume : 1.0;
            panicKey = data.panic_key || 'esc';

            updateKnobVisual(masterVolume);
            panicKeyBadge.textContent = panicKey.toUpperCase();
            panicKeyInput.value = panicKey;

            renderNumpadGrids();
        } catch (err) {
            console.error('Error loading sounds:', err);
        }
    }

    async function loadDevices() {
        try {
            const res = await fetch('/api/devices');
            const data = await res.json();
            
            primaryDeviceSelect.innerHTML = '<option value="">Default Windows Playback Device</option>';
            secondaryDeviceSelect.innerHTML = '<option value="">Select CABLE Input (VB-Audio Virtual Cable)...</option>';

            let autoSelectVirtualCable = null;

            data.devices.forEach(dev => {
                const optPrimary = document.createElement('option');
                optPrimary.value = dev.name;
                optPrimary.textContent = `${dev.name} (${dev.hostapi})`;
                if (dev.name === data.current_primary || dev.display_name === data.current_primary) optPrimary.selected = true;
                primaryDeviceSelect.appendChild(optPrimary);

                const optSec = document.createElement('option');
                optSec.value = dev.name;
                optSec.textContent = `${dev.name} (${dev.hostapi})`;
                if (dev.name === data.current_secondary || dev.display_name === data.current_secondary) optSec.selected = true;
                if (!data.current_secondary && dev.name.includes('CABLE Input')) {
                    autoSelectVirtualCable = dev.name;
                }
                secondaryDeviceSelect.appendChild(optSec);
            });

            if (autoSelectVirtualCable && !data.current_secondary) {
                secondaryDeviceSelect.value = autoSelectVirtualCable;
            }

            secondaryToggle.checked = !!data.secondary_enabled;
        } catch (err) {
            console.error('Error loading devices:', err);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Render 3 Numpad Grids (7,8,9 / 4,5,6 / 1,2,3 / 0 (span-2), .)
    // ─────────────────────────────────────────────────────────────────────────
    function renderNumpadGrids() {
        gridCtrl.innerHTML = '';
        gridAlt.innerHTML = '';
        gridCtrlAlt.innerHTML = '';

        soundCounter.textContent = `${sounds.length} sounds`;

        sounds.forEach(sound => {
            const card = createNumpadCard(sound);
            const mod = (sound.modifier || '').toLowerCase();

            if (mod === 'ctrl') {
                gridCtrl.appendChild(card);
            } else if (mod === 'alt') {
                gridAlt.appendChild(card);
            } else {
                gridCtrlAlt.appendChild(card);
            }
        });
    }

    function createNumpadCard(sound) {
        const card = document.createElement('div');
        card.id = `card-${sound.id}`;
        
        // 0 key spans 2 columns like a real physical numpad
        const isZeroKey = sound.symbol === '0' || (sound.hotkey && sound.hotkey.endsWith('0'));
        const spanClass = isZeroKey ? 'col-span-2' : 'col-span-1';

        card.className = `numpad-key p-3 flex flex-col justify-between gap-2.5 ${spanClass} ${
            activePlayingIds.has(sound.id) ? 'playing' : ''
        }`;

        const isPlaying = activePlayingIds.has(sound.id);
        const symbolText = sound.symbol || sound.name.charAt(0).toUpperCase();
        const hotkeyText = sound.hotkey ? sound.hotkey.toUpperCase() : 'NO KEY';

        const curVol = sound.volume !== undefined ? sound.volume : 1.0;
        const curPitch = sound.pitch || 0;
        const curSpeed = sound.speed || 1.0;

        card.innerHTML = `
            <div>
                <!-- Top Key Header: Symbol Badge + Delete -->
                <div class="flex items-center justify-between gap-1 mb-1">
                    <div class="flex items-center gap-1.5">
                        <span class="w-6 h-6 rounded-md bg-[#10141f] border border-[#2b354d] text-cyan-400 font-mono font-bold text-xs flex items-center justify-center shadow-inner">${symbolText}</span>
                        <button class="hotkey-badge text-[10px]" title="Click to rebind hotkey">${hotkeyText}</button>
                    </div>
                    <button class="delete-sound-btn text-slate-500 hover:text-red-400 p-0.5 opacity-0 hover:opacity-100 transition" title="Delete sound">
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
                <!-- Sound Name -->
                <h3 class="font-bold text-slate-100 text-xs leading-snug line-clamp-2" title="${sound.name}">${sound.name}</h3>
            </div>

            <!-- Action Bar: Play/Stop + FX Accordion Toggle -->
            <div class="flex items-center justify-between gap-2 pt-1 border-t border-[#222a3d]">
                <button class="play-btn-neon play-btn px-2.5 py-1.5 text-xs font-bold flex items-center gap-1 shadow-sm active:scale-95 transition" title="${isPlaying ? 'Stop' : 'Play Sound'}">
                    ${isPlaying ? `
                        <svg class="w-3.5 h-3.5 text-red-400" fill="currentColor" viewBox="0 0 24 24">
                            <rect x="6" y="6" width="12" height="12" rx="2"/>
                        </svg>
                        <span>Stop</span>
                    ` : `
                        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                        <span>Play</span>
                    `}
                </button>

                <button class="toggle-fx-btn text-[11px] text-slate-400 hover:text-cyan-400 font-semibold transition flex items-center gap-0.5">
                    <span>FX</span>
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                </button>
            </div>

            <!-- Sliders Drawer with HIGH VISIBILITY Tracks & Reset Buttons -->
            <div class="fx-panel hidden space-y-2 pt-2 border-t border-[#222a3d] text-xs text-slate-400">
                <!-- Volume Slider -->
                <div class="space-y-0.5">
                    <div class="flex items-center justify-between text-[10px]">
                        <span class="font-semibold text-slate-300">Vol:</span>
                        <div class="flex items-center gap-1">
                            <span class="vol-label font-mono text-cyan-300 font-bold">${Math.round(curVol * 100)}%</span>
                            <button class="reset-vol-btn reset-btn" title="Reset Volume to 100%">↺</button>
                        </div>
                    </div>
                    <input type="range" class="sound-vol-slider slider-cyan" min="0" max="1.5" step="0.05" value="${curVol}">
                </div>

                <!-- Pitch Slider -->
                <div class="space-y-0.5">
                    <div class="flex items-center justify-between text-[10px]">
                        <span class="font-semibold text-slate-300">Pitch:</span>
                        <div class="flex items-center gap-1">
                            <span class="pitch-val font-mono text-cyan-300 font-bold">${curPitch > 0 ? '+' : ''}${curPitch} st</span>
                            <button class="reset-pitch-btn reset-btn" title="Reset Pitch to 0 st">↺</button>
                        </div>
                    </div>
                    <input type="range" class="sound-pitch-slider" min="-12" max="12" step="1" value="${curPitch}">
                </div>

                <!-- Speed Slider -->
                <div class="space-y-0.5">
                    <div class="flex items-center justify-between text-[10px]">
                        <span class="font-semibold text-slate-300">Speed:</span>
                        <div class="flex items-center gap-1">
                            <span class="speed-val font-mono text-pink-400 font-bold">${curSpeed.toFixed(2)}x</span>
                            <button class="reset-speed-btn reset-btn" title="Reset Speed to 1.00x">↺</button>
                        </div>
                    </div>
                    <input type="range" class="sound-speed-slider slider-pink" min="0.5" max="2.0" step="0.05" value="${curSpeed}">
                </div>
            </div>
        `;

        // Card Listeners
        const playBtn = card.querySelector('.play-btn');
        const hotkeyBadge = card.querySelector('.hotkey-badge');
        const deleteBtn = card.querySelector('.delete-sound-btn');
        const toggleFxBtn = card.querySelector('.toggle-fx-btn');
        const fxPanel = card.querySelector('.fx-panel');

        const volSlider = card.querySelector('.sound-vol-slider');
        const volLabel = card.querySelector('.vol-label');
        const resetVolBtn = card.querySelector('.reset-vol-btn');

        const pitchSlider = card.querySelector('.sound-pitch-slider');
        const pitchVal = card.querySelector('.pitch-val');
        const resetPitchBtn = card.querySelector('.reset-pitch-btn');

        const speedSlider = card.querySelector('.sound-speed-slider');
        const speedVal = card.querySelector('.speed-val');
        const resetSpeedBtn = card.querySelector('.reset-speed-btn');

        // Play / Stop
        playBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (activePlayingIds.has(sound.id)) {
                stopSound(sound.id);
            } else {
                playFromBrowser(sound);
            }
        });

        // Rebind Hotkey
        hotkeyBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            openRebindModal(sound);
        });

        // Delete
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (confirm(`Delete "${sound.name}"?`)) {
                deleteSound(sound.id);
            }
        });

        // Toggle FX drawer
        toggleFxBtn.addEventListener('click', () => {
            fxPanel.classList.toggle('hidden');
        });

        // Volume Slider & Reset
        volSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            sound.volume = val;
            volLabel.textContent = `${Math.round(val * 100)}%`;
            updateSoundConfig(sound.id, { volume: val });
        });

        resetVolBtn.addEventListener('click', () => {
            sound.volume = 1.0;
            volSlider.value = 1.0;
            volLabel.textContent = '100%';
            updateSoundConfig(sound.id, { volume: 1.0 });
        });

        // Pitch Slider & Reset
        pitchSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            sound.pitch = val;
            pitchVal.textContent = `${val > 0 ? '+' : ''}${val} st`;
            updateSoundConfig(sound.id, { pitch: val });
        });

        resetPitchBtn.addEventListener('click', () => {
            sound.pitch = 0;
            pitchSlider.value = 0;
            pitchVal.textContent = '0 st';
            updateSoundConfig(sound.id, { pitch: 0 });
        });

        // Speed Slider & Reset
        speedSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            sound.speed = val;
            speedVal.textContent = `${val.toFixed(2)}x`;
            updateSoundConfig(sound.id, { speed: val });
        });

        resetSpeedBtn.addEventListener('click', () => {
            sound.speed = 1.0;
            speedSlider.value = 1.0;
            speedVal.textContent = '1.00x';
            updateSoundConfig(sound.id, { speed: 1.0 });
        });

        return card;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Playback Logic (Browser Click applies Global FX; Hotkeys use per-clip FX)
    // ─────────────────────────────────────────────────────────────────────────
    async function playFromBrowser(sound) {
        // Browser click combines individual sound settings with Global FX controls
        const gPitch = parseInt(globalPitchSlider.value) || 0;
        const gSpeed = parseFloat(globalSpeedSlider.value) || 1.0;

        const effectivePitch = (sound.pitch || 0) + gPitch;
        const effectiveSpeed = (sound.speed || 1.0) * gSpeed;
        const effectiveVol = (sound.volume !== undefined ? sound.volume : 1.0);

        setCardPlayingVisual(sound.id, true);

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
            console.error('Browser playback error:', err);
        }

        setTimeout(() => {
            setCardPlayingVisual(sound.id, false);
        }, 1800);
    }

    function setCardPlayingVisual(soundId, isPlaying) {
        if (isPlaying) {
            activePlayingIds.add(soundId);
        } else {
            activePlayingIds.delete(soundId);
        }

        const card = document.getElementById(`card-${soundId}`);
        if (!card) return;

        if (isPlaying) {
            card.classList.add('playing');
            const playBtn = card.querySelector('.play-btn');
            if (playBtn) {
                playBtn.innerHTML = `
                    <svg class="w-3.5 h-3.5 text-red-400" fill="currentColor" viewBox="0 0 24 24">
                        <rect x="6" y="6" width="12" height="12" rx="2"/>
                    </svg>
                    <span>Stop</span>
                `;
            }
        } else {
            card.classList.remove('playing');
            const playBtn = card.querySelector('.play-btn');
            if (playBtn) {
                playBtn.innerHTML = `
                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                    <span>Play</span>
                `;
            }
        }
    }

    async function stopSound(soundId) {
        setCardPlayingVisual(soundId, false);
        try {
            await fetch(`/api/sounds/${soundId}/stop`, { method: 'POST' });
        } catch (err) {
            console.error('Stop error:', err);
        }
    }

    async function panicStopAll() {
        activePlayingIds.clear();
        document.querySelectorAll('.numpad-key').forEach(c => {
            c.classList.remove('playing');
            const playBtn = c.querySelector('.play-btn');
            if (playBtn) {
                playBtn.innerHTML = `
                    <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                    <span>Play</span>
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
                renderNumpadGrids();
            }
        } catch (err) {
            console.error('Delete sound error:', err);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Gold Rotary Knob Interaction (Drag, Wheel, Click)
    // ─────────────────────────────────────────────────────────────────────────
    function updateKnobVisual(vol) {
        // Map 0.0 -> -135deg, 1.0 -> 135deg (270 deg total sweep)
        const angle = -135 + (vol * 270);
        knobIndicator.style.transform = `translateX(-50%) rotate(${angle}deg)`;
        volumeKnob.style.transform = `rotate(${angle}deg)`;
        masterVolVal.textContent = `${Math.round(vol * 100)}%`;
    }

    function setupRotaryKnob() {
        let isDraggingKnob = false;
        let startY = 0;
        let startVol = masterVolume;

        volumeKnob.addEventListener('mousedown', (e) => {
            isDraggingKnob = true;
            startY = e.clientY;
            startVol = masterVolume;
            e.preventDefault();
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDraggingKnob) return;
            const deltaY = startY - e.clientY; // drag up = increase volume
            let newVol = Math.max(0.0, Math.min(1.0, startVol + (deltaY / 120)));
            masterVolume = newVol;
            updateKnobVisual(newVol);
        });

        window.addEventListener('mouseup', async () => {
            if (isDraggingKnob) {
                isDraggingKnob = false;
                await fetch('/api/master_volume', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ volume: masterVolume })
                });
            }
        });

        // Wheel support on volume knob
        volumeKnob.addEventListener('wheel', async (e) => {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.05 : -0.05;
            masterVolume = Math.max(0.0, Math.min(1.0, masterVolume + delta));
            updateKnobVisual(masterVolume);
            await fetch('/api/master_volume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volume: masterVolume })
            });
        });

        // Master Mute button
        masterMuteBtn.addEventListener('click', async () => {
            if (masterVolume > 0) {
                masterVolume = 0;
            } else {
                masterVolume = 1.0;
            }
            updateKnobVisual(masterVolume);
            await fetch('/api/master_volume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volume: masterVolume })
            });
        });
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
        keyDisplay.classList.add('text-cyan-300');
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
                renderNumpadGrids();
                closeRebindModal();
            } else {
                alert(data.message || 'Error rebinding hotkey');
            }
        } catch (err) {
            console.error('Rebind error:', err);
        }
    }

    window.addEventListener('keydown', (e) => {
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
        if (['control', 'alt', 'shift', 'meta'].includes(key)) {
            keyDisplay.textContent = modifiers.join('+').toUpperCase() + ' + ...';
            return;
        }

        if (e.code.startsWith('Numpad')) {
            key = e.code.replace('Numpad', '').toLowerCase();
        }

        const fullCombo = [...modifiers, key].join('+');
        keyDisplay.textContent = fullCombo.toUpperCase();
        finalizeRebind(fullCombo);
    });

    clearHotkeyBtn.addEventListener('click', () => finalizeRebind(null));
    cancelRebindBtn.addEventListener('click', closeRebindModal);

    // ─────────────────────────────────────────────────────────────────────────
    // General Event Listeners & Modals
    // ─────────────────────────────────────────────────────────────────────────
    function setupEventListeners() {
        panicStopBtn.addEventListener('click', panicStopAll);

        // Global Pitch
        globalPitchSlider.addEventListener('input', (e) => {
            const val = e.target.value;
            globalPitchVal.textContent = `${val > 0 ? '+' : ''}${val} st`;
        });

        resetGlobalPitchBtn.addEventListener('click', () => {
            globalPitchSlider.value = 0;
            globalPitchVal.textContent = '0 st';
        });

        // Global Speed
        globalSpeedSlider.addEventListener('input', (e) => {
            globalSpeedVal.textContent = `${parseFloat(e.target.value).toFixed(2)}x`;
        });

        resetGlobalSpeedBtn.addEventListener('click', () => {
            globalSpeedSlider.value = 1.0;
            globalSpeedVal.textContent = '1.00x';
        });

        // Presets
        fxPresetBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const pitch = btn.dataset.pitch;
                const speed = btn.dataset.speed;
                globalPitchSlider.value = pitch;
                globalPitchVal.textContent = `${pitch > 0 ? '+' : ''}${pitch} st`;
                globalSpeedSlider.value = speed;
                globalSpeedVal.textContent = `${parseFloat(speed).toFixed(2)}x`;
            });
        });

        // Modals
        openSettingsBtn.addEventListener('click', () => settingsModal.classList.remove('hidden'));
        openUploadBtn.addEventListener('click', () => uploadModal.classList.remove('hidden'));

        document.querySelectorAll('.close-modal-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                settingsModal.classList.add('hidden');
                uploadModal.classList.add('hidden');
                closeRebindModal();
            });
        });

        // Audio Settings Save
        saveAudioSettingsBtn.addEventListener('click', async () => {
            const primary = primaryDeviceSelect.value !== '' ? primaryDeviceSelect.value : null;
            const secondary = secondaryDeviceSelect.value !== '' ? secondaryDeviceSelect.value : null;
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
                alert('Audio routing to Speakers & Virtual Cable saved successfully!');
                settingsModal.classList.add('hidden');
            } catch (err) {
                console.error('Save audio settings error:', err);
            }
        });

        // Panic Key Save
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

        // Test Chime
        testAudioRoutingBtn.addEventListener('click', async () => {
            if (sounds.length > 0) {
                await playFromBrowser(sounds[0]);
            }
        });

        // Dropzone Upload
        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('border-cyan-500', 'bg-cyan-950/20');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('border-cyan-500', 'bg-cyan-950/20');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('border-cyan-500', 'bg-cyan-950/20');
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

        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files || fileInput.files.length === 0) {
                alert('Please select an audio file.');
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('name', uploadNameInput.value);
            formData.append('hotkey', uploadHotkeyInput.value);

            try {
                const res = await fetch('/api/sounds/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.status === 'success') {
                    sounds.push(data.sound);
                    renderNumpadGrids();
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

    init();
});
