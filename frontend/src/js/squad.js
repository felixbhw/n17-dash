document.addEventListener('DOMContentLoaded', async () => {
    try {
        const squadGrid = document.getElementById('squad-grid');
        const tableBody = document.getElementById('table-body');
        const toggleButton = document.getElementById('toggle-view');
        const template = document.getElementById('player-card-template');

        // Debug: Log initial element references
        console.log('Initial elements:', {
            squadGrid,
            tableBody,
            toggleButton,
            template,
            squadTable: document.getElementById('squad-table')
        });

        let isTableView = false;

        // Move toggle button handler before fetch to ensure it's always set up
        toggleButton.addEventListener('click', () => {
            console.log('Toggle button clicked. Current view:', isTableView ? 'Table' : 'Grid');
            isTableView = !isTableView;
            
            // Debug: Log elements before toggling
            console.log('Elements before toggle:', {
                squadGrid: squadGrid.classList.contains('hidden'),
                squadTable: document.getElementById('squad-table').classList.contains('hidden')
            });
            
            squadGrid.classList.toggle('hidden', isTableView);
            document.getElementById('squad-table').classList.toggle('hidden', !isTableView);
            
            // Debug: Log elements after toggling
            console.log('Elements after toggle:', {
                squadGrid: squadGrid.classList.contains('hidden'),
                squadTable: document.getElementById('squad-table').classList.contains('hidden')
            });
            
            toggleButton.textContent = isTableView ? 'Switch to Grid View' : 'Switch to Table View';
        });

        // Fetch all player files from the data directory
        const response = await fetch('/api/squad');
        const allPlayers = await response.json();

        // Filter to only include squad players and sort by number
        const players = allPlayers
            .filter(player => player.is_squad_player !== false)  // Keep undefined (legacy) or true
            .sort((a, b) => (a.number || 99) - (b.number || 99));

        // Populate both grid and table
        players.forEach(player => {
            // Grid View Card
            const card = template.content.cloneNode(true);
            card.querySelector('.player-photo').style.backgroundImage = `url(${player.photo})`;
            card.querySelector('.player-name').textContent = player.name;
            card.querySelector('.player-number').textContent = player.number || 'N/A';
            card.querySelector('.player-position').textContent = player.position;
            card.querySelector('.player-age').textContent = player.age;
            card.querySelector('.player-link').href = `/player/${player.id}`;
            squadGrid.appendChild(card);

            // Table View Row
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${player.number || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="flex-shrink-0 h-10 w-10">
                            <div class="player-photo h-10 w-10 rounded-full bg-gray-200 bg-cover bg-center" 
                                 style="background-image: url('${player.photo}')"></div>
                        </div>
                        <div class="ml-4">
                            <div class="text-sm font-medium text-gray-900">${player.name}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${player.position}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${player.age}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <a href="/player/${player.id}" class="text-blue-600 hover:text-blue-900">View Details</a>
                </td>
            `;
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading squad data:', error);
        const errorMessage = `
            <div class="col-span-full text-center text-red-600 py-8">
                Error loading squad data. Please try again later.
            </div>
        `;
        squadGrid.innerHTML = errorMessage;
        document.getElementById('squad-table').innerHTML = errorMessage;
    }
});

// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.querySelector('[aria-controls="mobile-menu"]');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            const isExpanded = mobileMenuButton.getAttribute('aria-expanded') === 'true';
            mobileMenuButton.setAttribute('aria-expanded', !isExpanded);
            mobileMenu.classList.toggle('hidden');
        });
    }
});
