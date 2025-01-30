document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Get player ID from URL
        const playerId = window.location.pathname.split('/').pop();
        
        // Fetch player data
        const playerResponse = await fetch(`/api/player/${playerId}`);
        const player = await playerResponse.json();
        
        // Update player details
        document.querySelector('.player-photo').style.backgroundImage = `url(${player.photo})`;
        document.querySelector('.player-name').textContent = player.name;
        document.querySelector('.player-number').textContent = `#${player.number || 'N/A'}`;
        document.querySelector('.player-position').textContent = player.position;
        document.querySelector('.player-age').textContent = player.age;
        document.querySelector('.player-nationality').textContent = player.nationality;
        document.querySelector('.player-height').textContent = player.height;
        document.querySelector('.player-weight').textContent = player.weight;
        
        // Update page title
        document.title = `${player.name} - N17 Dashboard`;
        
        // Fetch player stats
        const statsResponse = await fetch(`/api/stats/${playerId}`);
        const stats = await statsResponse.json();
        
        // Create stats grid
        const statsContainer = document.getElementById('stats-container');
        
        if (stats.length === 0) {
            statsContainer.innerHTML = '<p class="text-gray-500">No statistics available for this player.</p>';
            return;
        }
        
        // Group stats by team
        const statsByTeam = stats.reduce((acc, stat) => {
            if (!acc[stat.team]) {
                acc[stat.team] = [];
            }
            acc[stat.team].push(stat);
            return acc;
        }, {});
        
        // Create stats table for each team
        Object.entries(statsByTeam).forEach(([team, teamStats]) => {
            const totalStats = teamStats.reduce((acc, stat) => {
                Object.entries(stat).forEach(([key, value]) => {
                    if (typeof value === 'number') {
                        acc[key] = (acc[key] || 0) + value;
                    }
                });
                return acc;
            }, {});
            
            const statsHtml = `
                <div class="mb-8 last:mb-0">
                    <h4 class="text-lg font-semibold mb-4">${team}</h4>
                    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <div class="text-sm font-medium text-gray-500">Appearances</div>
                            <div class="mt-1 text-2xl font-semibold">${totalStats.appearances || 0}</div>
                        </div>
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <div class="text-sm font-medium text-gray-500">Goals</div>
                            <div class="mt-1 text-2xl font-semibold">${totalStats.goals || 0}</div>
                        </div>
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <div class="text-sm font-medium text-gray-500">Assists</div>
                            <div class="mt-1 text-2xl font-semibold">${totalStats.assists || 0}</div>
                        </div>
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <div class="text-sm font-medium text-gray-500">Minutes Played</div>
                            <div class="mt-1 text-2xl font-semibold">${totalStats.minutes || 0}</div>
                        </div>
                    </div>
                </div>
            `;
            
            statsContainer.insertAdjacentHTML('beforeend', statsHtml);
        });
        
    } catch (error) {
        console.error('Error loading player data:', error);
        const main = document.querySelector('main');
        main.innerHTML = `
            <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                <div class="px-4 py-6 sm:px-0">
                    <div class="text-center text-red-600 py-8">
                        Error loading player data. Please try again later.
                    </div>
                </div>
            </div>
        `;
    }
});
