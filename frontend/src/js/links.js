// Initialize DataTables
let playerLinksTable;
let timelineTable;
let editingPlayer = null;

function formatDate(dateString) {
    return moment(dateString).fromNow();
}

function getBadgeHtml(type, value) {
    if (!value) return '';
    const badgeClasses = {
        status: {
            'hearsay': 'bg-secondary',
            'rumors': 'bg-info',
            'developing': 'bg-warning',
            'here we go!': 'bg-success',
            'archived': 'bg-dark'
        },
        direction: {
            'incoming': 'bg-success',
            'outgoing': 'bg-danger'
        }
    };
    
    const badgeClass = badgeClasses[type][value.toLowerCase()] || 'bg-secondary';
    return `<span class="badge ${badgeClass}">${value}</span>`;
}

function formatClubs(clubs) {
    if (!clubs || !clubs.length) return '';
    
    return clubs.map(club => {
        const roleClass = {
            'current': 'bg-primary',
            'destination': 'bg-success',
            'interested': 'bg-info'
        }[club.role] || 'bg-secondary';
        
        return `<div class="mb-1">
            <span class="badge ${roleClass}">${club.name}</span>
        </div>`;
    }).join('');
}

function initTables() {
    playerLinksTable = $('#playerLinksTable').DataTable({
        ajax: {
            url: '/api/links/players',
            dataSrc: ''
        },
        columns: [
            { 
                data: 'canonical_name',
                render: function(data, type, row) {
                    return `<a href="#" class="player-link" data-player-id="${row.player_id}">${data}</a>`;
                }
            },
            { 
                data: 'transfer_status',
                render: function(data) {
                    return getBadgeHtml('status', data);
                }
            },
            { 
                data: 'direction',
                render: function(data) {
                    return getBadgeHtml('direction', data);
                }
            },
            { 
                data: 'timeline',
                render: function(data) {
                    if (!data || !data.length) return 'No events';
                    return data[data.length - 1].details;
                }
            },
            { 
                data: 'related_clubs',
                render: formatClubs
            },
            { 
                data: 'last_updated',
                render: formatDate
            },
            {
                data: null,
                orderable: false,
                className: 'text-center',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `
                            <div class="btn-group" role="group">
                                <button type="button" class="btn btn-sm btn-primary edit-player" data-player-id="${row.player_id}">
                                    <i class="fas fa-edit"></i> Edit
                                </button>
                                <button type="button" class="btn btn-sm btn-success add-event" data-player-id="${row.player_id}">
                                    <i class="fas fa-plus"></i> Add
                                </button>
                            </div>
                        `;
                    }
                    return '';
                }
            }
        ],
        order: [[5, 'desc']]
    });

    timelineTable = $('#timelineTable').DataTable({
        ajax: {
            url: '/api/links/events',
            dataSrc: ''
        },
        columns: [
            { 
                data: 'date',
                render: formatDate
            },
            { data: 'player_name' },
            { 
                data: 'event_type',
                render: function(data) {
                    return getBadgeHtml('status', data);
                }
            },
            { 
                data: 'details',
                render: function(data, type, row) {
                    if (type === 'display' && row.news_ids && row.news_ids.length > 0) {
                        return `<a href="/news/${row.news_ids[0]}" class="text-decoration-none">
                            ${data}
                            <i class="fas fa-external-link-alt ms-1 small"></i>
                        </a>`;
                    }
                    return data;
                }
            },
            { 
                data: 'confidence',
                render: function(data) {
                    const confidence = parseInt(data) || 0;
                    const badgeClass = confidence > 75 ? 'bg-success' : 
                                     confidence > 50 ? 'bg-warning' : 
                                     confidence > 25 ? 'bg-info' : 'bg-secondary';
                    return `<span class="badge ${badgeClass}">${confidence}%</span>`;
                }
            },
            {
                data: null,
                orderable: false,
                className: 'text-center',
                render: function(data, type, row, meta) {
                    if (type === 'display') {
                        return `
                            <div class="btn-group" role="group">
                                <button type="button" class="btn btn-sm btn-danger delete-event" 
                                        data-player-id="${data.player_id}"
                                        data-event-index="${meta.row}">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </div>
                        `;
                    }
                    return '';
                }
            }
        ],
        order: [[0, 'desc']]
    });
}

function populateEditModal(playerId) {
    editingPlayer = playerId;
    
    $.get(`/api/links/player/${playerId}`)
        .done(function(data) {
            $('#editPlayerId').val(playerId).prop('readonly', false);  // Make ID editable
            $('#editStatus').val(data.transfer_status || '');
            $('#editDirection').val(data.direction || '');
            
            $('#editClubs').empty();
            if (data.related_clubs && data.related_clubs.length) {
                data.related_clubs.forEach(club => {
                    addClubEntry(club.name, club.role);
                });
            }
            
            $('#editPlayerModal').modal('show');
        })
        .fail(function(jqXHR) {
            alert('Error loading player data: ' + jqXHR.responseText);
        });
}

function addClubEntry(name = '', role = 'interested') {
    const template = document.getElementById('clubTemplate');
    const clone = template.content.cloneNode(true);
    
    const clubEntry = clone.querySelector('.club-entry');
    const nameInput = clone.querySelector('.club-name');
    const roleSelect = clone.querySelector('.club-role');
    
    nameInput.value = name;
    roleSelect.value = role;
    
    $('#editClubs').append(clubEntry);
}

function savePlayerChanges() {
    const oldPlayerId = editingPlayer;
    const newPlayerId = parseInt($('#editPlayerId').val());
    
    const data = {
        player_id: newPlayerId,  // Include new ID in update
        transfer_status: $('#editStatus').val(),
        direction: $('#editDirection').val(),
        related_clubs: []
    };
    
    $('#editClubs .club-entry').each(function() {
        const name = $(this).find('.club-name').val();
        const role = $(this).find('.club-role').val();
        if (name) {
            data.related_clubs.push({ name, role });
        }
    });
    
    $.ajax({
        url: `/api/links/player/${oldPlayerId}`,
        method: 'PUT',
        contentType: 'application/json',
        data: JSON.stringify(data)
    })
    .done(function() {
        $('#editPlayerModal').modal('hide');
        playerLinksTable.ajax.reload();
        timelineTable.ajax.reload();
    })
    .fail(function(jqXHR) {
        alert('Error saving changes: ' + jqXHR.responseText);
    });
}

function saveNewEvent() {
    const playerId = $('#eventPlayerId').val();
    if (!playerId) return;
    
    const newsId = $('#eventNewsId').val().trim();
    const data = {
        event_type: $('#eventType').val(),
        details: $('#eventDetails').val(),
        confidence: parseInt($('#eventConfidence').val()) || 50,
        news_ids: newsId ? [newsId] : []
    };
    
    $.ajax({
        url: `/api/links/player/${playerId}/timeline`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data)
    })
    .done(function() {
        $('#addEventModal').modal('hide');
        playerLinksTable.ajax.reload();
        timelineTable.ajax.reload();
    })
    .fail(function(jqXHR) {
        alert('Error adding event: ' + jqXHR.responseText);
    });
}

function deleteEvent(playerId, eventIndex) {
    if (!confirm('Are you sure you want to delete this event?')) return;
    
    $.ajax({
        url: `/api/links/player/${playerId}/timeline/${eventIndex}`,
        method: 'DELETE'
    })
    .done(function() {
        playerLinksTable.ajax.reload();
        timelineTable.ajax.reload();
    })
    .fail(function(jqXHR) {
        alert('Error deleting event: ' + jqXHR.responseText);
    });
}

function refreshData() {
    return new Promise((resolve, reject) => {
        try {
            // Create a counter to track completed reloads
            let completed = 0;
            const total = 2;

            // Function to check if all reloads are done
            const checkComplete = () => {
                completed++;
                if (completed === total) {
                    resolve();
                }
            };

            // Reload both tables
            playerLinksTable.ajax.reload(checkComplete);
            timelineTable.ajax.reload(checkComplete);
        } catch (error) {
            reject(error);
        }
    });
}

$(document).ready(function() {
    // Initialize DataTables
    initTables();
    
    // Add Club button
    $('#addClubBtn').click(function() {
        addClubEntry();
    });
    
    // Edit player button - Use event delegation for dynamically added elements
    $(document).on('click', '.edit-player', function() {
        const playerId = $(this).data('player-id');
        populateEditModal(playerId);
    });
    
    // Add event button - Use event delegation for dynamically added elements
    $(document).on('click', '.add-event', function() {
        const playerId = $(this).data('player-id');
        $('#eventPlayerId').val(playerId);
        $('#eventDetails').val('');
        $('#eventConfidence').val(50);
        $('#addEventModal').modal('show');
    });
    
    // Delete event button - Use event delegation for dynamically added elements
    $(document).on('click', '.delete-event', function() {
        const playerId = $(this).data('player-id');
        const eventIndex = $(this).data('event-index');
        deleteEvent(playerId, eventIndex);
    });
    
    // Save buttons
    $('#savePlayerBtn').click(savePlayerChanges);
    $('#saveEventBtn').click(saveNewEvent);
    
    // Remove club button - Use event delegation
    $(document).on('click', '.remove-club', function() {
        $(this).closest('.club-entry').remove();
    });

    // Add Player button handler
    $('#addPlayerBtn').click(function() {
        $('#newPlayerName').val('');
        $('#newPlayerId').val('');
        $('#addPlayerModal').modal('show');
    });
    
    // Save new player handler
    $('#saveNewPlayerBtn').click(function() {
        const name = $('#newPlayerName').val().trim();
        const id = $('#newPlayerId').val().trim();
        
        if (!name || !id) {
            alert('Please fill in all fields');
            return;
        }
        
        $.ajax({
            url: '/api/links/players/manual',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: name,
                player_id: parseInt(id)
            })
        })
        .done(function() {
            $('#addPlayerModal').modal('hide');
            playerLinksTable.ajax.reload();
            timelineTable.ajax.reload();
        })
        .fail(function(jqXHR) {
            alert('Error creating player: ' + jqXHR.responseText);
        });
    });
    
    // Link news button handler
    $(document).on('click', '.link-news', function() {
        const playerId = $(this).data('player-id');
        $('#linkNewsPlayerId').val(playerId);
        $('#linkNewsId').val('');
        $('#linkNewsModal').modal('show');
    });
    
    // Save news link handler
    $('#saveLinkNewsBtn').click(function() {
        const playerId = $('#linkNewsPlayerId').val();
        const newsId = $('#linkNewsId').val().trim();
        
        if (!newsId) {
            alert('Please enter a news ID');
            return;
        }
        
        $.ajax({
            url: `/api/links/player/${playerId}/link-news`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                news_id: newsId
            })
        })
        .done(function() {
            $('#linkNewsModal').modal('hide');
            playerLinksTable.ajax.reload();
            timelineTable.ajax.reload();
        })
        .fail(function(jqXHR) {
            alert('Error linking news: ' + jqXHR.responseText);
        });
    });
    
    // Update refresh button handler to include unlinked news processing
    $('#refreshNewsBtn').click(function() {
        const $btn = $(this);
        
        $btn.prop('disabled', true)
            .html('<i class="fas fa-spinner fa-spin me-2"></i>Checking...');
            
        // First process new news
        $.ajax({
            url: '/api/reddit/check-now',
            method: 'POST'
        })
        .then(() => {
            // Then reprocess unlinked news
            return $.ajax({
                url: '/api/links/reprocess-unlinked',
                method: 'POST'
            });
        })
        .then(() => refreshData())
        .then(() => {
            $btn.removeClass('btn-primary')
                .addClass('btn-success')
                .html('<i class="fas fa-check me-2"></i>Updated!');
        })
        .catch((error) => {
            console.error('Error:', error);
            $btn.removeClass('btn-primary')
                .addClass('btn-danger')
                .html('<i class="fas fa-exclamation-triangle me-2"></i>Error');
        })
        .always(() => {
            setTimeout(() => {
                $btn.prop('disabled', false)
                    .removeClass('btn-success btn-danger')
                    .addClass('btn-primary')
                    .html('<i class="fas fa-sync-alt me-2"></i>Check for New Updates');
            }, 2000);
        });
    });
}); 