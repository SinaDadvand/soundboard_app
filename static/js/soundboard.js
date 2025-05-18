document.addEventListener('DOMContentLoaded', () => {
    const soundButtons = document.querySelectorAll('.sound-button');
    const audioElements = new Map();
    let currentlyPlaying = null;

    // Initialize audio elements and keyboard shortcuts
    soundButtons.forEach((button, index) => {
        const soundFile = button.dataset.sound;
        const audio = new Audio(`/audio/${soundFile}`);
        audioElements.set(button, audio);

        // Add keyboard shortcut hint
        const keyNumber = index + 1;
        if (keyNumber <= 9) {
            button.querySelector('.key-hint').textContent = `Press ${keyNumber}`;
        }
    });

    // Function to play sound
    function playSound(button) {
        const audio = audioElements.get(button);
        
        // Stop currently playing sound if any
        if (currentlyPlaying) {
            currentlyPlaying.pause();
            currentlyPlaying.currentTime = 0;
            currentlyPlaying.parentButton.classList.remove('active');
        }

        // Play new sound
        audio.currentTime = 0;
        audio.play();
        button.classList.add('active');
        
        // Store reference to currently playing audio
        audio.parentButton = button;
        currentlyPlaying = audio;

        // Remove active class when sound finishes
        audio.onended = () => {
            button.classList.remove('active');
            currentlyPlaying = null;
        };
    }

    // Click event listeners
    soundButtons.forEach(button => {
        button.addEventListener('click', () => playSound(button));
    });

    // Keyboard event listeners
    document.addEventListener('keydown', (event) => {
        const keyNumber = parseInt(event.key);
        if (!isNaN(keyNumber) && keyNumber >= 1 && keyNumber <= 9) {
            const button = soundButtons[keyNumber - 1];
            if (button) {
                playSound(button);
            }
        }
    });
});
