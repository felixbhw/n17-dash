document.addEventListener('DOMContentLoaded', async () => {
    try {
        const squadGrid = document.getElementById('squad-grid');
        const squadTable = document.getElementById('squad-table');
        const tableBody = document.getElementById('table-body');
        const toggleButton = document.getElementById('toggle-view');
        const template = document.getElementById('player-card-template');

        let isTableView = false;
        let dataTable = null;

        // Fetch all player files from the data directory
        const response = await fetch('/api/squad');
        const allPlayers = await response.json();

        // Sort by number
        const players = allPlayers.sort((a, b) => (a.number || 99) - (b.number || 99));

        // Populate grid view
        players.forEach(player => {
            const card = template.content.cloneNode(true);
            card.querySelector('.player-photo').style.backgroundImage = `url(${player.photo})`;
            card.querySelector('.player-name').textContent = player.name;
            card.querySelector('.player-number').textContent = player.number || 'N/A';
            card.querySelector('.player-position').textContent = player.position;
            card.querySelector('.player-age').textContent = player.age;
            card.querySelector('.player-link').href = `/player/${player.id}/stats`;
            squadGrid.appendChild(card);

            // Create table row
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${player.number || 'N/A'}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="me-3" style="width: 40px; height: 40px;">
                            <div class="rounded-circle bg-light" 
                                 style="width: 100%; height: 100%; background-image: url('${player.photo}'); background-size: cover; background-position: center;"></div>
                        </div>
                        <div>${player.name}</div>
                    </div>
                </td>
                <td>${player.position}</td>
                <td>${player.age}</td>
                <td>
                    <a href="/player/${player.id}/stats" class="btn btn-sm btn-outline-primary">View Stats</a>
                </td>
            `;
            tableBody.appendChild(row);
        });

        // Initialize DataTable
        dataTable = new DataTable('#squadTable', {
            paging: true,
            ordering: true,
            info: true,
            pageLength: 25,
            order: [[0, 'asc']],
            language: {
                search: "Search squad:",
                lengthMenu: "Show _MENU_ players",
                info: "Showing _START_ to _END_ of _TOTAL_ players",
                infoEmpty: "No players found",
                infoFiltered: "(filtered from _MAX_ total players)"
            }
        });

        // Toggle view handler
        toggleButton.addEventListener('click', () => {
            isTableView = !isTableView;
            
            if (isTableView) {
                squadGrid.style.display = 'none';
                squadTable.style.display = 'block';
                toggleButton.textContent = 'Switch to Grid View';
                if (dataTable) {
                    dataTable.columns.adjust();
                }
            } else {
                squadGrid.style.display = 'flex';
                squadTable.style.display = 'none';
                toggleButton.textContent = 'Switch to Table View';
            }
        });

    } catch (error) {
        console.error('Error loading squad data:', error);
        const errorMessage = `
            <div class="alert alert-danger text-center m-4">
                Error loading squad data. Please try again later.
            </div>
        `;
        squadGrid.innerHTML = errorMessage;
        squadTable.innerHTML = errorMessage;
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
