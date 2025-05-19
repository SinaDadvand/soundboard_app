document.addEventListener('DOMContentLoaded', () => {
    const soundButtons = document.querySelectorAll('.sound-button');
    let currentlyPlaying = null;

    // Function to play sound through the server endpoint
    async function playSound(button) {
        const soundFile = button.dataset.sound;
        
        // Remove active class from previous button if any
        if (currentlyPlaying) {
            currentlyPlaying.classList.remove('active');
        }

        // Play new sound through server endpoint
        try {
            const response = await fetch(`/play/${soundFile}`);
            if (response.ok) {
                button.classList.add('active');
                currentlyPlaying = button;
                
                // Remove active class after 1 second
                setTimeout(() => {
                    button.classList.remove('active');
                    if (currentlyPlaying === button) {
                        currentlyPlaying = null;
                    }
                }, 1000);
            }
        } catch (error) {
            console.error('Error playing sound:', error);
        }
    }

    // Click event listeners
    soundButtons.forEach(button => {
        button.addEventListener('click', () => playSound(button));
    });
});
