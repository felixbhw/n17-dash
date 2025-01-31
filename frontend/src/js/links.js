// Initialize DataTables when document is ready
$(document).ready(function() {
    // Initialize player links table
    const playerLinksTable = $('#playerLinksTable').DataTable({
        order: [[6, 'desc']], // Sort by last updated by default
        pageLength: 25,
        columns: [
            { // Player
                data: 'name',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `<a href="/player/${row.id}">${data}</a>`;
                    }
                    return data;
                }
            },
            { // Current Club
                data: 'current_club',
                defaultContent: '-'
            },
            { // Direction
                data: 'direction',
                render: function(data, type, row) {
                    if (type === 'display') {
                        if (data === 'incoming') {
                            return '<span class="badge bg-success">Incoming</span>';
                        } else if (data === 'outgoing') {
                            return '<span class="badge bg-danger">Outgoing</span>';
                        }
                        return '-';
                    }
                    return data;
                }
            },
            { // Type
                data: 'transfer_type',
                render: function(data, type, row) {
                    if (type === 'display') {
                        switch(data) {
                            case 'transfer':
                                return '<span class="badge bg-primary">Transfer</span>';
                            case 'loan':
                                return '<span class="badge bg-info">Loan</span>';
                            case 'loan_with_option':
                                return '<span class="badge bg-warning">Loan + Option</span>';
                            case 'loan_with_obligation':
                                return '<span class="badge bg-warning">Loan + Obligation</span>';
                            default:
                                return '<span class="badge bg-secondary">Unclear</span>';
                        }
                    }
                    return data;
                }
            },
            { // Latest Price
                data: 'latest_price',
                render: function(data, type, row) {
                    if (!data || !data.amount) return '-';
                    return `${data.amount.toLocaleString()} ${data.currency}`;
                }
            },
            { // Links Count
                data: 'links_count',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `<span class="badge bg-primary">${data}</span>`;
                    }
                    return data;
                }
            },
            { // Last Updated
                data: 'last_updated',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return new Date(data).toLocaleString();
                    }
                    return data;
                }
            }
        ]
    });

    // Initialize events table
    const eventsTable = $('#eventsTable').DataTable({
        order: [[0, 'desc']], // Sort by date descending
        pageLength: 10,
        columns: [
            { // Date
                data: 'date',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return new Date(data).toLocaleString();
                    }
                    return data;
                }
            },
            { // Player
                data: 'player_name',
                render: function(data, type, row) {
                    if (type === 'display' && row.player_id) {
                        return `<a href="/player/${row.player_id}">${data}</a>`;
                    }
                    return data;
                }
            },
            { // Event
                data: 'event_type',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `<span class="badge bg-info">${data}</span>`;
                    }
                    return data;
                }
            },
            { // Details
                data: 'details'
            },
            { // Source
                data: 'source',
                render: function(data, type, row) {
                    if (type === 'display' && row.source_url) {
                        return `<a href="${row.source_url}" target="_blank">${data}</a>`;
                    }
                    return data;
                }
            }
        ]
    });

    // Function to fetch and update data
    function updateTables() {
        // Fetch player links data
        fetch('/api/links/players')
            .then(response => response.json())
            .then(data => {
                playerLinksTable.clear().rows.add(data).draw();
            })
            .catch(error => console.error('Error fetching player links:', error));

        // Fetch events data
        fetch('/api/links/events')
            .then(response => response.json())
            .then(data => {
                eventsTable.clear().rows.add(data).draw();
            })
            .catch(error => console.error('Error fetching events:', error));
    }

    // Initial data load
    updateTables();

    // Refresh data every 5 minutes
    setInterval(updateTables, 5 * 60 * 1000);
}); 