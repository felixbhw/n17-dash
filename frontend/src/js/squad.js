document.addEventListener('DOMContentLoaded', async () => {
    try {
        const squadGrid = document.getElementById('squad-grid');
        const template = document.getElementById('player-card-template');

        // Fetch all player files from the data directory
        const response = await fetch('/api/squad');
        const players = await response.json();

        // Sort players by squad number
        players.sort((a, b) => (a.number || 99) - (b.number || 99));

        players.forEach(player => {
            const card = template.content.cloneNode(true);
            
            // Set player photo
            const photoDiv = card.querySelector('.player-photo');
            photoDiv.style.backgroundImage = `url(${player.photo})`;
            
            // Set player details
            card.querySelector('.player-name').textContent = player.name;
            card.querySelector('.player-number').textContent = player.number || 'N/A';
            card.querySelector('.player-position').textContent = player.position;
            card.querySelector('.player-age').textContent = player.age;
            
            // Set link to player details page
            const link = card.querySelector('.player-link');
            link.href = `/player/${player.id}`;
            
            squadGrid.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading squad data:', error);
        const squadGrid = document.getElementById('squad-grid');
        squadGrid.innerHTML = `
            <div class="col-span-full text-center text-red-600 py-8">
                Error loading squad data. Please try again later.
            </div>
        `;
    }
});
