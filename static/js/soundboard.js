/**
 * Virtual Soundboard Numpad Pro - Frontend Controller
 * ==================================================
 * - 2 Instant Output Destination Toggles (Headset & Virtual Cable)
 * - Compact single-line keycaps (Hotkey Left, Track Title Right)
 * - Gold Rotary Knob with Dot indicator
 * - Vertical Global FX Rack on the side
 * - High-contrast slider tracks & individual reset buttons
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let sounds = [];
    let masterVolume = 1.0;
    let panicKey = 'esc';
    let headsetEnabled = true;
    let cableEnabled = true;
    let isRebinding = false;
    let rebindingSoundId = null;
    let activePlayingIds = new Set();

    // DOM Grids
    const gridCtrl = document.getElementById('grid-ctrl');
    const gridAlt = document.getElementById('grid-alt');
    const gridCtrlAlt = document.getElementById('grid-ctrl-alt');
    const soundCounter = document.getElementById('sound-counter-badge');

    // Destination Toggles
    const toggleHeadsetBtn = document.getElementById('toggle-headset-btn');
    const toggleCableBtn = document.getElementById('toggle-cable-btn');

    // Rotary Knob Elements
    const volumeKnob = document.getElementById('volume-knob');
    const knobIndicator = document.getElementById('knob-indicator');
    const masterVolVal = document.getElementById('master-volume-val');
    const masterMuteBtn = document.getElementById('master-mute-btn');
    const panicStopBtn = document.getElementById('panic-stop-btn');
    const panicKeyBadge = document.getElementById('panic-key-badge');

    // Vertical Global FX Elements
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

    // Rebind Elements
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
        setupDestinationToggles();
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
            
            primaryDeviceSelect.innerHTML = '<option value="">Default Headphones / WF-1000XM4</option>';
            secondaryDeviceSelect.innerHTML = '<option value="">CABLE Input (VB-Audio Virtual Cable)</option>';

            data.devices.forEach(dev => {
                const optPrimary = document.createElement('option');
                optPrimary.value = dev.name;
                optPrimary.textContent = `${dev.name} (${dev.hostapi})`;
                if (dev.name === data.current_primary) optPrimary.selected = true;
                primaryDeviceSelect.appendChild(optPrimary);

                const optSec = document.createElement('option');
                optSec.value = dev.name;
                optSec.textContent = `${dev.name} (${dev.hostapi})`;
                if (dev.name === data.current_secondary) optSec.selected = true;
                secondaryDeviceSelect.appendChild(optSec);
            });
        } catch (err) {
            console.error('Error loading devices:', err);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Render Compact Numpad Grids
    // ─────────────────────────────────────────────────────────────────────────
    function renderNumpadGrids() {
        gridCtrl.innerHTML = '';
        gridAlt.innerHTML = '';
        gridCtrlAlt.innerHTML = '';

        soundCounter.textContent = `${sounds.length} sounds`;

        sounds.forEach(sound => {
            const card = createCompactNumpadCard(sound);
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

    function createCompactNumpadCard(sound) {
        const card = document.createElement('div');
        card.id = `card-${sound.id}`;
        
        const isZeroKey = sound.symbol === '0' || (sound.hotkey && sound.hotkey.endsWith('0'));
        const spanClass = isZeroKey ? 'col-span-2' : 'col-span-1';

        card.className = `numpad-key p-2.5 flex flex-col justify-between gap-2 ${spanClass} ${
            activePlayingIds.has(sound.id) ? 'playing' : ''
        }`;

        const isPlaying = activePlayingIds.has(sound.id);
        const hotkeyText = sound.hotkey ? sound.hotkey.toUpperCase() : 'NO KEY';
        const curVol = sound.volume !== undefined ? sound.volume : 1.0;
        const curPitch = sound.pitch || 0;
        const curSpeed = sound.speed || 1.0;

        card.innerHTML = `
            <!-- Single Row Header: Hotkey Left, Track Title Right -->
            <div class="flex items-center justify-between gap-1.5 w-full">
                <button class="hotkey-badge" title="Click to rebind hotkey">${hotkeyText}</button>
                <h3 class="font-bold text-slate-200 text-xs truncate max-w-[120px] text-right" title="${sound.name}">${sound.name}</h3>
            </div>

            <!-- Action Row: Play/Stop + FX Drawer Button -->
            <div class="flex items-center justify-between gap-2 pt-1 border-t border-[#222a3d]">
                <button class="play-btn-neon play-btn px-2 py-1 text-[11px] font-bold flex items-center gap-1 shadow-sm active:scale-95 transition" title="${isPlaying ? 'Stop' : 'Play Sound'}">
                    ${isPlaying ? `
                        <svg class="w-3 h-3 text-red-400" fill="currentColor" viewBox="0 0 24 24">
                            <rect x="6" y="6" width="12" height="12" rx="2"/>
                        </svg>
                        <span>Stop</span>
                    ` : `
                        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                        <span>Play</span>
                    `}
                </button>

                <button class="toggle-fx-btn text-[10px] text-slate-400 hover:text-cyan-400 font-semibold transition flex items-center gap-0.5">
                    <span>FX</span>
                    <svg class="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                </button>
            </div>

            <!-- Sliders Drawer with High-Visibility Tracks & Individual Resets -->
            <div class="fx-panel hidden space-y-1.5 pt-1.5 border-t border-[#222a3d] text-xs text-slate-400">
                <!-- Volume -->
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

                <!-- Pitch -->
                <div class="space-y-0.5">
                    <div class="flex items-center justify-between text-[10px]">
                        <span class="font-semibold text-slate-300">Pitch:</span>
                        <div class="flex items-center gap-1">
                            <span class="pitch-val font-mono text-cyan-300 font-bold">${curPitch > 0 ? '+' : ''}${curPitch}st</span>
                            <button class="reset-pitch-btn reset-btn" title="Reset Pitch to 0 st">↺</button>
                        </div>
                    </div>
                    <input type="range" class="sound-pitch-slider" min="-12" max="12" step="1" value="${curPitch}">
                </div>

                <!-- Speed -->
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

        const playBtn = card.querySelector('.play-btn');
        const hotkeyBadge = card.querySelector('.hotkey-badge');
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

        // Toggle FX drawer
        toggleFxBtn.addEventListener('click', () => {
            fxPanel.classList.toggle('hidden');
        });

        // Volume
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

        // Pitch
        pitchSlider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            sound.pitch = val;
            pitchVal.textContent = `${val > 0 ? '+' : ''}${val}st`;
            updateSoundConfig(sound.id, { pitch: val });
        });

        resetPitchBtn.addEventListener('click', () => {
            sound.pitch = 0;
            pitchSlider.value = 0;
            pitchVal.textContent = '0st';
            updateSoundConfig(sound.id, { pitch: 0 });
        });

        // Speed
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
    // Destination Toggles (Headset & Virtual Cable)
    // ─────────────────────────────────────────────────────────────────────────
    function setupDestinationToggles() {
        toggleHeadsetBtn.addEventListener('click', async () => {
            headsetEnabled = !headsetEnabled;
            toggleHeadsetBtn.classList.toggle('active', headsetEnabled);
            await syncDestinationToggles();
        });

        toggleCableBtn.addEventListener('click', async () => {
            cableEnabled = !cableEnabled;
            toggleCableBtn.classList.toggle('active', cableEnabled);
            await syncDestinationToggles();
        });
    }

    async function syncDestinationToggles() {
        try {
            await fetch('/api/routing_toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    headset_enabled: headsetEnabled,
                    cable_enabled: cableEnabled
                })
            });
        } catch (err) {
            console.error('Error syncing destination toggles:', err);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Playback Logic
    // ─────────────────────────────────────────────────────────────────────────
    async function playFromBrowser(sound) {
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
                    <svg class="w-3 h-3 text-red-400" fill="currentColor" viewBox="0 0 24 24">
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
                    <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
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
                    <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
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

    // ─────────────────────────────────────────────────────────────────────────
    // Gold Rotary Knob with Dot
    // ─────────────────────────────────────────────────────────────────────────
    function updateKnobVisual(vol) {
        const angle = -135 + (vol * 270);
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
            const deltaY = startY - e.clientY;
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

        masterMuteBtn.addEventListener('click', async () => {
            masterVolume = masterVolume > 0 ? 0 : 1.0;
            updateKnobVisual(masterVolume);
            await fetch('/api/master_volume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volume: masterVolume })
            });
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Rebind Modal
    // ─────────────────────────────────────────────────────────────────────────
    function openRebindModal(sound) {
        isRebinding = true;
        rebindingSoundId = sound.id;
        rebindSoundName.textContent = `Clip: ${sound.name}`;
        keyDisplay.textContent = sound.hotkey ? `Current: ${sound.hotkey.toUpperCase()}` : 'Listening for keys...';
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
    // General Event Listeners
    // ─────────────────────────────────────────────────────────────────────────
    function setupEventListeners() {
        panicStopBtn.addEventListener('click', panicStopAll);

        // Vertical Global Pitch
        globalPitchSlider.addEventListener('input', (e) => {
            const val = e.target.value;
            globalPitchVal.textContent = `${val > 0 ? '+' : ''}${val} st`;
        });

        resetGlobalPitchBtn.addEventListener('click', () => {
            globalPitchSlider.value = 0;
            globalPitchVal.textContent = '0 st';
        });

        // Vertical Global Speed
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

        // Settings Save
        saveAudioSettingsBtn.addEventListener('click', async () => {
            const primary = primaryDeviceSelect.value !== '' ? primaryDeviceSelect.value : null;
            const secondary = secondaryDeviceSelect.value !== '' ? secondaryDeviceSelect.value : null;

            try {
                await fetch('/api/devices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        primary_device: primary,
                        secondary_device: secondary,
                        secondary_enabled: true
                    })
                });
                alert('Audio device settings saved!');
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
