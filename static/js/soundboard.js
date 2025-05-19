document.addEventListener('DOMContentLoaded', () => {
    const soundButtons = document.querySelectorAll('.sound-button');

    // Function to play sound and show visual feedback
    function playSound(button) {
        // Make API call to play the sound
        fetch(`/play/${button.dataset.sound}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Add visual feedback
                    button.classList.add('active');
                    setTimeout(() => {
                        button.classList.remove('active');
                    }, 200);
                }
            })
            .catch(error => console.error('Error:', error));
    }

    // Click event listeners
    soundButtons.forEach(button => {
        button.addEventListener('click', () => playSound(button));
    });
});
