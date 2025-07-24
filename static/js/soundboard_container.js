document.addEventListener('DOMContentLoaded', () => {
    const soundButtons = document.querySelectorAll('.sound-button');
    let audioContext = null;
    let audioBuffers = new Map();
    let hotKeyMap = new Map();

    // Initialize Web Audio API
    function initializeAudio() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        return audioContext;
    }

    // Preload audio files
    async function preloadAudio(filename) {
        if (audioBuffers.has(filename)) {
            return audioBuffers.get(filename);
        }

        try {
            const response = await fetch(`/audio/${filename}`);
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            audioBuffers.set(filename, audioBuffer);
            return audioBuffer;
        } catch (error) {
            console.error('Error loading audio:', error);
            return null;
        }
    }

    // Play audio using Web Audio API
    async function playAudioBuffer(filename) {
        const ctx = initializeAudio();
        
        // Resume context if suspended (required by some browsers)
        if (ctx.state === 'suspended') {
            await ctx.resume();
        }

        const audioBuffer = await preloadAudio(filename);
        if (!audioBuffer) return;

        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);
        source.start(0);
    }

    // Alternative: Play audio using HTML5 Audio (fallback)
    function playAudioHTML5(filename) {
        const audio = new Audio(`/audio/${filename}`);
        audio.play().catch(error => {
            console.error('Error playing audio:', error);
        });
    }

    // Function to play sound and show visual feedback
    async function playSound(button) {
        if (!button) return;
        
        const filename = button.dataset.sound;
        
        try {
            // Try Web Audio API first, fallback to HTML5 Audio
            if (window.AudioContext || window.webkitAudioContext) {
                await playAudioBuffer(filename);
            } else {
                playAudioHTML5(filename);
            }

            // Add visual feedback
            button.classList.add('active');
            setTimeout(() => {
                button.classList.remove('active');
            }, 200);

        } catch (error) {
            console.error('Error playing sound:', error);
            // Fallback to HTML5 audio
            playAudioHTML5(filename);
        }
    }

    // Build hotkey map
    function buildHotKeyMap() {
        soundButtons.forEach(button => {
            const hotkey = button.dataset.hotkey;
            if (hotkey) {
                hotKeyMap.set(hotkey, button);
            }
        });
    }

    // Handle keyboard events
    function handleKeyPress(event) {
        // Prevent default behavior for our hotkeys
        const key = event.key.toLowerCase();
        let combination = '';

        // Build key combination string
        if (event.ctrlKey && event.altKey) {
            combination = `ctrl+alt+${key}`;
        } else if (event.ctrlKey) {
            combination = `ctrl+${key}`;
        } else if (event.altKey) {
            combination = `alt+${key}`;
        }

        // Check if this combination exists in our hotkey map
        if (combination && hotKeyMap.has(combination)) {
            event.preventDefault();
            const button = hotKeyMap.get(combination);
            playSound(button);
        }
    }

    // Preload all audio files for better performance
    async function preloadAllAudio() {
        console.log('Preloading audio files...');
        const promises = Array.from(soundButtons).map(button => {
            const filename = button.dataset.sound;
            return preloadAudio(filename);
        });
        
        try {
            await Promise.all(promises);
            console.log('All audio files preloaded successfully');
        } catch (error) {
            console.warn('Some audio files failed to preload:', error);
        }
    }

    // Initialize everything
    function initialize() {
        // Build hotkey mapping
        buildHotKeyMap();
        
        // Add click event listeners
        soundButtons.forEach(button => {
            button.addEventListener('click', () => playSound(button));
        });

        // Add keyboard event listeners
        document.addEventListener('keydown', handleKeyPress);

        // Initialize audio context on first user interaction
        document.addEventListener('click', () => {
            initializeAudio();
            preloadAllAudio();
        }, { once: true });

        console.log(`Soundboard initialized with ${soundButtons.length} sounds`);
        console.log('Click anywhere to initialize audio system');
    }

    // Start the application
    initialize();

    // Add some helpful console information
    console.log('🎵 Virtual Soundboard (Container Mode) loaded');
    console.log('💡 Hotkeys work when this browser tab is focused');
    console.log('🐳 Audio plays through your browser');
    
    // API endpoint monitoring for external hotkey client
    let lastPlayRequest = 0;
    
    // Function to handle external play requests
    async function handleExternalPlayRequest() {
        try {
            const response = await fetch('/api/sounds');
            const soundsData = await response.json();
            
            // Check for new play requests from hotkey client
            const urlParams = new URLSearchParams(window.location.search);
            const playSound = urlParams.get('play');
            
            if (playSound && Date.now() - lastPlayRequest > 100) {
                lastPlayRequest = Date.now();
                
                // Find button for this sound
                const targetButton = Array.from(soundButtons).find(button => 
                    button.dataset.sound === playSound
                );
                
                if (targetButton) {
                    await playSound(targetButton);
                    console.log('🎵 External play request:', playSound);
                }
                
                // Clear the URL parameter
                window.history.replaceState({}, document.title, window.location.pathname);
            }
            
        } catch (error) {
            console.warn('Error checking for external play requests:', error);
        }
    }
    
    // Monitor for external play requests
    setInterval(handleExternalPlayRequest, 250);
    
    // Enhanced focus handling for better hotkey client support
    window.addEventListener('focus', () => {
        console.log('🔍 Window focused - hotkey client requests will work better');
        initializeAudio();
    });
    
    // Message listener for postMessage API
    window.addEventListener('message', async (event) => {
        if (event.origin !== window.location.origin) return;
        
        if (event.data.type === 'PLAY_SOUND') {
            const soundFile = event.data.sound;
            const targetButton = Array.from(soundButtons).find(button => 
                button.dataset.sound === soundFile
            );
            
            if (targetButton) {
                await playSound(targetButton);
                console.log('🎵 PostMessage play request:', soundFile);
            }
        }
        
        if (event.data.type === 'ACTIVATE_AUDIO') {
            initializeAudio();
            await preloadAllAudio();
            console.log('🔊 Audio system activated via external request');
        }
    });
});
