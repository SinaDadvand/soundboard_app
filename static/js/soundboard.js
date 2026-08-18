/**
 * Virtual Soundboard Numpad Pro - Frontend Controller
 * ==================================================
 * - 3 Stacked Vertical Numpad Groups (Full width, clear legible cards)
 * - 3 Hardware Rotary Knobs on top (Volume Gold, Pitch Cyan, Speed Pink)
 * - 2 Instant Output Destination Toggles (Headset & Virtual Cable)
 * - Micro Presets Box
 * - Individual card volume/pitch/speed FX with individual ↺ reset buttons
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let sounds = [];
    let masterVolume = 1.0;
    let globalPitch = 0;       // -12 to +12 semitones
    let globalSpeed = 1.0;      // 0.5 to 2.0x
    let globalEcho = 0.0;       // 0.0 to 1.0 (0% to 100%)
    let globalReverb = 0.0;     // 0.0 to 1.0 (0% to 100%)
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
    const toggleDiscordBtn = document.getElementById('toggle-discord-btn');
    const discordBtnLabel = document.getElementById('discord-btn-label');
    const discordModalStatusBadge = document.getElementById('discord-modal-status-badge');
    const discordTokenInput = document.getElementById('discord-token-input');
    const saveDiscordTokenBtn = document.getElementById('save-discord-token-btn');
    const discordChannelSelect = document.getElementById('discord-channel-select');
    const discordJoinBtn = document.getElementById('discord-join-btn');

    // 5 Hardware Knobs Elements
    const volumeKnob = document.getElementById('volume-knob');
    const volumeIndicator = document.getElementById('volume-indicator');
    const masterVolVal = document.getElementById('master-volume-val');

    const pitchKnob = document.getElementById('pitch-knob');
    const pitchIndicator = document.getElementById('pitch-indicator');
    const globalPitchVal = document.getElementById('global-pitch-val');
    const resetPitchKnobBtn = document.getElementById('reset-pitch-knob-btn');

    const speedKnob = document.getElementById('speed-knob');
    const speedIndicator = document.getElementById('speed-indicator');
    const globalSpeedVal = document.getElementById('global-speed-val');
    const resetSpeedKnobBtn = document.getElementById('reset-speed-knob-btn');

    const echoKnob = document.getElementById('echo-knob');
    const echoIndicator = document.getElementById('echo-indicator');
    const globalEchoVal = document.getElementById('global-echo-val');
    const resetEchoKnobBtn = document.getElementById('reset-echo-knob-btn');

    const reverbKnob = document.getElementById('reverb-knob');
    const reverbIndicator = document.getElementById('reverb-indicator');
    const globalReverbVal = document.getElementById('global-reverb-val');
    const resetReverbKnobBtn = document.getElementById('reset-reverb-knob-btn');

    const fxPresetBtns = document.querySelectorAll('.fx-preset-btn');
    const panicStopBtn = document.getElementById('panic-stop-btn');
    const panicKeyBadge = document.getElementById('panic-key-badge');

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
        setupKnobs();
        setupDestinationToggles();
    }

    async function loadSounds() {
        try {
            const res = await fetch('/api/status');
            const statusData = await res.json();
            
            masterVolume = statusData.master_volume !== undefined ? statusData.master_volume : 1.0;
            globalPitch = statusData.global_pitch !== undefined ? statusData.global_pitch : 0.0;
            globalSpeed = statusData.global_speed !== undefined ? statusData.global_speed : 1.0;
            globalEcho = statusData.global_echo !== undefined ? statusData.global_echo : 0.0;
            globalReverb = statusData.global_reverb !== undefined ? statusData.global_reverb : 0.0;
            panicKey = statusData.panic_key || 'esc';

            updateVolumeKnobVisual(masterVolume);
            updatePitchKnobVisual(globalPitch);
            updateSpeedKnobVisual(globalSpeed);
            updateEchoKnobVisual(globalEcho);
            updateReverbKnobVisual(globalReverb);

            panicKeyBadge.textContent = panicKey.toUpperCase();
            panicKeyInput.value = panicKey;

            const sRes = await fetch('/api/sounds');
            const sData = await sRes.json();
            sounds = sData.sounds || [];

            renderNumpadGrids();
        } catch (err) {
            console.error('Error loading sounds:', err);
        }
    }

    async function loadDevices() {
        try {
            const res = await fetch('/api/devices');
            const data = await res.json();
            
            if (data.headset_enabled !== undefined) {
                headsetEnabled = Boolean(data.headset_enabled);
                toggleHeadsetBtn.classList.toggle('active', headsetEnabled);
            }
            if (data.cable_enabled !== undefined) {
                cableEnabled = Boolean(data.cable_enabled);
                toggleCableBtn.classList.toggle('active', cableEnabled);
            }

            primaryDeviceSelect.innerHTML = '<option value="">Sony Headset / Wireless Stereo Headset</option>';
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
    // Render Stacked Numpad Grids
    // ─────────────────────────────────────────────────────────────────────────
    function renderNumpadGrids() {
        gridCtrl.innerHTML = '';
        gridAlt.innerHTML = '';
        gridCtrlAlt.innerHTML = '';

        soundCounter.textContent = `${sounds.length} sounds`;

        const symbolOrder = ['7', '8', '9', '4', '5', '6', '1', '2', '3', '0', '.'];
        
        const getCardKeyRank = (sound) => {
            const sym = (sound.symbol || '').toString();
            const idx = symbolOrder.indexOf(sym);
            if (idx !== -1) return idx;
            if (sound.hotkey) {
                for (let i = 0; i < symbolOrder.length; i++) {
                    if (sound.hotkey.endsWith(symbolOrder[i])) return i;
                }
            }
            return sound.order !== undefined ? sound.order : 99;
        };

        const ctrlSounds = sounds.filter(s => (s.modifier || '').toLowerCase() === 'ctrl')
                                 .sort((a, b) => getCardKeyRank(a) - getCardKeyRank(b));
        const altSounds = sounds.filter(s => (s.modifier || '').toLowerCase() === 'alt')
                                .sort((a, b) => getCardKeyRank(a) - getCardKeyRank(b));
        const ctrlAltSounds = sounds.filter(s => (s.modifier || '').toLowerCase() === 'ctrl+alt')
                                    .sort((a, b) => getCardKeyRank(a) - getCardKeyRank(b));

        ctrlSounds.forEach(s => gridCtrl.appendChild(createNumpadCard(s)));
        altSounds.forEach(s => gridAlt.appendChild(createNumpadCard(s)));
        ctrlAltSounds.forEach(s => gridCtrlAlt.appendChild(createNumpadCard(s)));
    }

    function createNumpadCard(sound) {
        const card = document.createElement('div');
        card.id = `card-${sound.id}`;
        
        const isZeroKey = sound.symbol === '0' || (sound.hotkey && sound.hotkey.endsWith('0'));
        const spanClass = isZeroKey ? 'col-span-2' : 'col-span-1';

        card.className = `numpad-key p-3 flex flex-col justify-between gap-2.5 ${spanClass} ${
            activePlayingIds.has(sound.id) ? 'playing' : ''
        }`;

        const isPlaying = activePlayingIds.has(sound.id);
        const hotkeyText = sound.hotkey ? sound.hotkey.toUpperCase() : 'NO KEY';
        const curVol = sound.volume !== undefined ? sound.volume : 1.0;
        const curPitch = sound.pitch || 0;
        const curSpeed = sound.speed || 1.0;

        card.innerHTML = `
            <!-- Single Row Header: Hotkey Left, Full Sound Title Right -->
            <div class="flex items-center justify-between gap-2 w-full">
                <button class="hotkey-badge" title="Click to rebind hotkey">${hotkeyText}</button>
                <h3 class="font-bold text-slate-100 text-xs md:text-sm truncate text-right flex-1" title="${sound.name}">${sound.name}</h3>
            </div>

            <!-- Action Row: Play/Stop + FX Drawer Button -->
            <div class="flex items-center justify-between gap-2 pt-1 border-t border-[#222a3d]">
                <button class="play-btn-neon play-btn px-3 py-1.5 text-xs font-bold flex items-center gap-1.5 shadow-sm active:scale-95 transition" title="${isPlaying ? 'Stop' : 'Play Sound'}">
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

                <button class="toggle-fx-btn text-xs text-slate-400 hover:text-cyan-400 font-semibold transition flex items-center gap-1">
                    <span>FX Controls</span>
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                </button>
            </div>

            <!-- Sliders Drawer with High-Visibility Tracks & Individual Resets -->
            <div class="fx-panel hidden space-y-2 pt-2 border-t border-[#222a3d] text-xs text-slate-400">
                <!-- Volume -->
                <div class="space-y-0.5">
                    <div class="flex items-center justify-between text-[11px]">
                        <span class="font-semibold text-slate-300">Volume:</span>
                        <div class="flex items-center gap-1">
                            <span class="vol-label font-mono text-cyan-300 font-bold">${Math.round(curVol * 100)}%</span>
                            <button class="reset-vol-btn reset-btn" title="Reset Volume to 100%">↺</button>
                        </div>
                    </div>
                    <input type="range" class="sound-vol-slider slider-cyan" min="0" max="1.5" step="0.05" value="${curVol}">
                </div>

                <!-- Pitch -->
                <div class="space-y-0.5">
                    <div class="flex items-center justify-between text-[11px]">
                        <span class="font-semibold text-slate-300">Pitch Shift:</span>
                        <div class="flex items-center gap-1">
                            <span class="pitch-val font-mono text-cyan-300 font-bold">${curPitch > 0 ? '+' : ''}${curPitch}st</span>
                            <button class="reset-pitch-btn reset-btn" title="Reset Pitch to 0 st">↺</button>
                        </div>
                    </div>
                    <input type="range" class="sound-pitch-slider" min="-12" max="12" step="1" value="${curPitch}">
                </div>

                <!-- Speed -->
                <div class="space-y-0.5">
                    <div class="flex items-center justify-between text-[11px]">
                        <span class="font-semibold text-slate-300">Playback Speed:</span>
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

        // Play (Multi-instance polyphonic)
        playBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            playFromBrowser(sound);
        });

        card.addEventListener('click', (e) => {
            if (e.target.closest('input') || e.target.closest('button')) return;
            playFromBrowser(sound);
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
            const res = await fetch('/api/routing_toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    headset_enabled: headsetEnabled,
                    cable_enabled: cableEnabled
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                headsetEnabled = Boolean(data.headset_enabled);
                cableEnabled = Boolean(data.cable_enabled);
                toggleHeadsetBtn.classList.toggle('active', headsetEnabled);
                toggleCableBtn.classList.toggle('active', cableEnabled);
            }
        } catch (err) {
            console.error('Error syncing destination toggles:', err);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Playback Logic
    // ─────────────────────────────────────────────────────────────────────────
    async function playFromBrowser(sound) {
        const soundPitch = (sound.pitch !== undefined ? sound.pitch : 0);
        const soundSpeed = (sound.speed !== undefined ? sound.speed : 1.0);
        const soundVol = (sound.volume !== undefined ? sound.volume : 1.0);

        setCardPlayingVisual(sound.id, true);

        try {
            await fetch(`/api/play/${sound.id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    volume: soundVol,
                    pitch: soundPitch,
                    speed: soundSpeed
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

    // ─────────────────────────────────────────────────────────────────────────
    // 5 Rotary Knobs: Volume, Pitch, Speed, Echo, Reverb
    // ─────────────────────────────────────────────────────────────────────────
    function updateVolumeKnobVisual(vol) {
        const angle = -135 + (vol * 270);
        volumeKnob.style.transform = `rotate(${angle}deg)`;
        masterVolVal.textContent = `${Math.round(vol * 100)}%`;
    }

    function updatePitchKnobVisual(pitch) {
        // -12 to +12 -> angle -135 to +135
        const norm = (pitch + 12) / 24.0;
        const angle = -135 + (norm * 270);
        pitchKnob.style.transform = `rotate(${angle}deg)`;
        globalPitchVal.textContent = `${pitch > 0 ? '+' : ''}${pitch} st`;
    }

    function updateSpeedKnobVisual(speed) {
        // 0.5 to 2.0 -> angle -135 to +135
        const norm = (speed - 0.5) / 1.5;
        const angle = -135 + (norm * 270);
        speedKnob.style.transform = `rotate(${angle}deg)`;
        globalSpeedVal.textContent = `${speed.toFixed(2)}x`;
    }

    function updateEchoKnobVisual(echo) {
        // 0.0 to 1.0 -> angle -135 to +135
        const angle = -135 + (echo * 270);
        echoKnob.style.transform = `rotate(${angle}deg)`;
        globalEchoVal.textContent = `${Math.round(echo * 100)}%`;
    }

    function updateReverbKnobVisual(reverb) {
        // 0.0 to 1.0 -> angle -135 to +135
        const angle = -135 + (reverb * 270);
        reverbKnob.style.transform = `rotate(${angle}deg)`;
        globalReverbVal.textContent = `${Math.round(reverb * 100)}%`;
    }

    let globalFxDebounceTimer = null;
    function syncGlobalFX() {
        clearTimeout(globalFxDebounceTimer);
        globalFxDebounceTimer = setTimeout(async () => {
            try {
                await fetch('/api/global_fx', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        pitch: globalPitch,
                        speed: globalSpeed,
                        echo: globalEcho,
                        reverb: globalReverb
                    })
                });
            } catch (err) {
                console.error('Error syncing global FX:', err);
            }
        }, 30);
    }

    function setupKnobs() {
        // Helper to bind rotary drag & wheel
        function bindKnob(element, initialValGetter, minVal, maxVal, step, onUpdate, onCommit) {
            let isDragging = false;
            let startY = 0;
            let startVal = 0;

            element.addEventListener('mousedown', (e) => {
                isDragging = true;
                startY = e.clientY;
                startVal = initialValGetter();
                e.preventDefault();
            });

            window.addEventListener('mousemove', (e) => {
                if (!isDragging) return;
                const deltaY = startY - e.clientY;
                const range = maxVal - minVal;
                let newVal = startVal + (deltaY / 120) * range;
                newVal = Math.max(minVal, Math.min(maxVal, newVal));
                if (step >= 1) newVal = Math.round(newVal);
                onUpdate(newVal);
            });

            window.addEventListener('mouseup', () => {
                if (isDragging) {
                    isDragging = false;
                    if (onCommit) onCommit();
                }
            });

            element.addEventListener('wheel', (e) => {
                e.preventDefault();
                const cur = initialValGetter();
                const delta = (e.deltaY < 0 ? 1 : -1) * (step || 0.05);
                let newVal = Math.max(minVal, Math.min(maxVal, cur + delta));
                if (step >= 1) newVal = Math.round(newVal);
                onUpdate(newVal);
                if (onCommit) onCommit();
            });
        }

        // 1. Volume Knob
        bindKnob(
            volumeKnob,
            () => masterVolume,
            0.0, 1.0, 0.05,
            (val) => { masterVolume = val; updateVolumeKnobVisual(val); },
            async () => {
                await fetch('/api/master_volume', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ volume: masterVolume })
                });
            }
        );

        // 2. Pitch Knob
        bindKnob(
            pitchKnob,
            () => globalPitch,
            -12, 12, 1,
            (val) => { globalPitch = val; updatePitchKnobVisual(val); syncGlobalFX(); }
        );

        resetPitchKnobBtn.addEventListener('click', () => {
            globalPitch = 0;
            updatePitchKnobVisual(0);
            syncGlobalFX();
        });

        // 3. Speed Knob
        bindKnob(
            speedKnob,
            () => globalSpeed,
            0.5, 2.0, 0.05,
            (val) => { globalSpeed = val; updateSpeedKnobVisual(val); syncGlobalFX(); }
        );

        resetSpeedKnobBtn.addEventListener('click', () => {
            globalSpeed = 1.0;
            updateSpeedKnobVisual(1.0);
            syncGlobalFX();
        });

        // 4. Echo Knob
        bindKnob(
            echoKnob,
            () => globalEcho,
            0.0, 1.0, 0.05,
            (val) => { globalEcho = val; updateEchoKnobVisual(val); syncGlobalFX(); }
        );

        resetEchoKnobBtn.addEventListener('click', () => {
            globalEcho = 0.0;
            updateEchoKnobVisual(0.0);
            syncGlobalFX();
        });

        // 5. Reverb Knob
        bindKnob(
            reverbKnob,
            () => globalReverb,
            0.0, 1.0, 0.05,
            (val) => { globalReverb = val; updateReverbKnobVisual(val); syncGlobalFX(); }
        );

        resetReverbKnobBtn.addEventListener('click', () => {
            globalReverb = 0.0;
            updateReverbKnobVisual(0.0);
            syncGlobalFX();
        });

        // Presets
        fxPresetBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                globalPitch = parseInt(btn.dataset.pitch) || 0;
                globalSpeed = parseFloat(btn.dataset.speed) || 1.0;
                globalEcho = parseFloat(btn.dataset.echo) || 0.0;
                globalReverb = parseFloat(btn.dataset.reverb) || 0.0;

                updatePitchKnobVisual(globalPitch);
                updateSpeedKnobVisual(globalSpeed);
                updateEchoKnobVisual(globalEcho);
                updateReverbKnobVisual(globalReverb);
                syncGlobalFX();
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

                // If a Discord channel is selected, join it
                if (discordChannelSelect && discordChannelSelect.value) {
                    await fetch('/api/discord/join', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ channel_id: discordChannelSelect.value })
                    });
                    await pollDiscordStatus();
                }

                alert('Settings saved and connected!');
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

        // Discord Bot Controls
        if (toggleDiscordBtn) {
            toggleDiscordBtn.addEventListener('click', async () => {
                const res = await fetch('/api/discord/status');
                const status = await res.json();
                if (!status.configured) {
                    settingsModal.classList.remove('hidden');
                    if (discordTokenInput) discordTokenInput.focus();
                } else if (status.voice_connected) {
                    await fetch('/api/discord/leave', { method: 'POST' });
                    await pollDiscordStatus();
                } else {
                    settingsModal.classList.remove('hidden');
                }
            });
        }

        if (saveDiscordTokenBtn) {
            saveDiscordTokenBtn.addEventListener('click', async () => {
                const token = discordTokenInput.value.trim();
                if (!token) return;
                saveDiscordTokenBtn.textContent = 'Connecting...';
                try {
                    const res = await fetch('/api/discord/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ token })
                    });
                    const data = await res.json();
                    saveDiscordTokenBtn.textContent = 'Connected!';
                    setTimeout(() => { saveDiscordTokenBtn.textContent = 'Connect'; }, 2000);
                    await pollDiscordStatus();
                } catch (err) {
                    console.error('Discord config error:', err);
                    saveDiscordTokenBtn.textContent = 'Connect';
                }
            });
        }

        if (discordJoinBtn) {
            discordJoinBtn.addEventListener('click', async () => {
                const channelId = discordChannelSelect.value;
                if (!channelId) {
                    alert('Please select a voice channel.');
                    return;
                }
                discordJoinBtn.textContent = 'Joining...';
                try {
                    const res = await fetch('/api/discord/join', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ channel_id: channelId })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        discordJoinBtn.textContent = 'Connected';
                        await pollDiscordStatus();
                    } else {
                        alert(data.message || 'Failed to join voice channel');
                        discordJoinBtn.textContent = 'Join Voice';
                    }
                } catch (err) {
                    console.error('Discord join error:', err);
                    discordJoinBtn.textContent = 'Join Voice';
                }
            });
        }

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
                    await loadSounds();
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
        // Discord Status Polling
        async function pollDiscordStatus() {
            try {
                const res = await fetch('/api/discord/status');
                const st = await res.json();

                if (toggleDiscordBtn && discordBtnLabel) {
                    if (st.voice_connected) {
                        toggleDiscordBtn.classList.add('active');
                        discordBtnLabel.textContent = `👾 #${st.channel_name || 'Voice'}`;
                    } else if (st.connected) {
                        toggleDiscordBtn.classList.remove('active');
                        discordBtnLabel.textContent = `👾 ${st.user ? st.user.split('#')[0] : 'Ready'}`;
                    } else {
                        toggleDiscordBtn.classList.remove('active');
                        discordBtnLabel.textContent = `👾 Discord`;
                    }
                }

                if (discordModalStatusBadge) {
                    if (st.voice_connected) {
                        discordModalStatusBadge.textContent = `Connected (${st.guild_name} ➔ #${st.channel_name})`;
                        discordModalStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 font-medium border border-emerald-800/50';
                    } else if (st.connected) {
                        discordModalStatusBadge.textContent = `Bot Ready (${st.user})`;
                        discordModalStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 font-medium border border-purple-800/50';
                    } else if (st.error) {
                        discordModalStatusBadge.textContent = `Error: ${st.error}`;
                        discordModalStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-red-950 text-red-300 font-medium border border-red-800/50';
                    } else if (st.is_connecting || st.configured) {
                        discordModalStatusBadge.textContent = 'Connecting...';
                        discordModalStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 font-medium';
                    } else {
                        discordModalStatusBadge.textContent = 'Idle (No Token)';
                        discordModalStatusBadge.className = 'text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-medium';
                    }
                }

                if (discordChannelSelect && st.available_channels && st.available_channels.length > 0) {
                    const currentVal = discordChannelSelect.value;
                    discordChannelSelect.innerHTML = '<option value="">Select Voice Channel...</option>';
                    st.available_channels.forEach(ch => {
                        const opt = document.createElement('option');
                        opt.value = ch.id;
                        opt.textContent = ch.name;
                        if (ch.id === st.channel_id || ch.id === currentVal) {
                            opt.selected = true;
                        }
                        discordChannelSelect.appendChild(opt);
                    });
                }
            } catch (err) {
                // Background poll ignore
            }
        }

        pollDiscordStatus();
        setInterval(pollDiscordStatus, 8000);
    }

    init();
});
