// ZooStudy Main JavaScript
// CSRF token and AJAX URLs are injected by base.html via window.ZOO_CONFIG

$(document).ready(function () {
    initShop();
    initTimer();
    initTaskToggle();
    initNotes();
    initFormWidgets();
});

// Shop: AJAX animal purchase
function initShop() {
    if (!$('.buy-btn').length) return;

    // Handle buy button click — POST to AJAX endpoint and update UI on success
    $('.buy-btn').on('click', function () {
        const btn = $(this);
        const animalId = btn.data('animal-id');

        btn.prop('disabled', true).text('Buying...');

        $.ajax({
            url: ZOO_CONFIG.urls.buyAnimal,
            method: 'POST',
            data: { animal_id: animalId, csrfmiddlewaretoken: ZOO_CONFIG.csrfToken },
            success: function (data) {
                if (data.success) {
                    showBuyMessage(data.message, 'success');
                    btn.removeClass('buy-btn').addClass('btn-owned').text('✓ Owned');
                    // Refresh coin display and disable buttons the user can no longer afford
                    $('.coin-display').text('🪙 ' + data.currency + ' coins');
                    updateAffordability(data.currency);
                } else {
                    showBuyMessage(data.message, 'error');
                    btn.prop('disabled', false).text('Buy (🪙 ' + btn.data('cost') + ')');
                }
            },
            error: function () {
                showBuyMessage('Something went wrong. Please try again.', 'error');
                btn.prop('disabled', false).text('Buy (🪙 ' + btn.data('cost') + ')');
            }
        });
    });

    // Disable/enable buy buttons based on the user's current coin balance
    function updateAffordability(currency) {
        $('.buy-btn').each(function () {
            const cost = parseInt($(this).data('cost'));
            if (currency < cost) {
                $(this).prop('disabled', true).attr('title', 'Not enough coins');
            } else {
                $(this).prop('disabled', false).removeAttr('title');
            }
        });
    }

    // Show a temporary toast notification in the bottom-right corner
    function showBuyMessage(msg, type) {
        const el = $('#buy-message');
        el.removeClass('success error').addClass(type).text(msg).fadeIn();
        setTimeout(function () { el.fadeOut(); }, 3000);
    }
}

// Study Hub: server-side timer with coin tracking (Frank)
function initTimer() {
    if (!$('#timer-display').length) return;

    let interval = null;

    function formatTime(s) {
        const h = String(Math.floor(s / 3600)).padStart(2, '0');
        const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
        const sec = String(s % 60).padStart(2, '0');
        return h + ':' + m + ':' + sec;
    }

    function updateTimer() {
        $.get(ZOO_CONFIG.urls.timerGet, function(data) {
            $('#timer-display').text(formatTime(data.elapsed));
            $('#timer-coins').text('🪙 ' + data.coins + ' coins earned');
        });
    }

    function showSessionToast(msg) {
        $('#session-toast').text(msg).fadeIn();
        setTimeout(function() { $('#session-toast').fadeOut(); }, 3000);
    }

    // On page load, check if a timer is already running on the server
    $.get(ZOO_CONFIG.urls.timerGet, function(data) {
        if (data.elapsed > 0) {
            $('#timer-display').text(formatTime(data.elapsed));
            $('#timer-coins').text('🪙 ' + data.coins + ' coins earned');
            $('#btn-start').hide();
            $('#btn-pause').show();
            $('#btn-stop').show();
            interval = setInterval(updateTimer, 1000);
        }
    });

    // Start
    $('#btn-start').on('click', function() {
        $.get(ZOO_CONFIG.urls.timerStart, function() {
            if (!interval) {
                interval = setInterval(updateTimer, 1000);
            }
            $('#btn-start').hide();
            $('#btn-pause').show();
            $('#btn-stop').show();
        });
    });

    // Pause / Resume toggle
    $('#btn-pause').on('click', function() {
        if ($('#btn-pause').text().trim().includes('Pause')) {
            $.get(ZOO_CONFIG.urls.timerPause, function() {
                clearInterval(interval);
                interval = null;
                $('#btn-pause').text('▶ Resume');
            });
        } else {
            $.get(ZOO_CONFIG.urls.timerResume, function() {
                if (!interval) {
                    interval = setInterval(updateTimer, 1000);
                }
                $('#btn-pause').text('⏸ Pause');
            });
        }
    });

    // Stop & Save
    $('#btn-stop').on('click', function() {
        $.get(ZOO_CONFIG.urls.timerStop, function(data) {
            clearInterval(interval);
            interval = null;
            if (data.coins_earned > 0) {
                showSessionToast('🎉 Session saved! +' + data.coins_earned + ' coins');
                setTimeout(function() { location.reload(); }, 2500);
            } else {
                showSessionToast('⚠️ Session too short (minimum 1 minute).');
            }
            $('#timer-display').text('00:00:00');
            $('#timer-coins').text('🪙 0 coins earned');
            $('#btn-start').show();
            $('#btn-pause').hide().text('⏸ Pause');
            $('#btn-stop').hide();
        });
    });
}

//Study Hub: AJAX task completion toggle
function initTaskToggle() {
    if (!$('.toggle-btn').length) return;

    // Use event delegation so dynamically-added task buttons also work
    $(document).on('click', '.toggle-btn', function () {
        const btn = $(this);
        const taskId = btn.data('task-id');
        const taskEl = $('#task-' + taskId);

        $.ajax({
            url: ZOO_CONFIG.urls.toggleTask,
            method: 'POST',
            data: { task_id: taskId, csrfmiddlewaretoken: ZOO_CONFIG.csrfToken },
            success: function (data) {
                if (data.success) {
                    if (data.completed) {// Mark task as done without a page reload for efficiency 
                        taskEl.addClass('completed').removeClass('overdue');
                        btn.text('Undo').data('completed', 'true');
                        taskEl.find('.badge-due, .badge-overdue').replaceWith('<span class="badge-done">✓ Done</span>');
                    } else {// Reload to recalculate deadlines when undoing
                        taskEl.removeClass('completed');
                        btn.text('Done').data('completed', 'false');
                        location.reload();
                    }
                }
            }
        });
    });
}

// Notes: toggle add-note form visibility per task
function initNotes() {
    if (!$('.toggle-form-btn').length) return;

    $('.toggle-form-btn').on('click', function () {
        const targetId = $(this).data('target');
        $('#' + targetId).slideToggle(200);
    });
}

// Apply Bootstrap form-control class to Django-rendered form widgets
function initFormWidgets() {
    $('input[name="title"]').addClass('form-control');
    $('input[name="deadline"]').addClass('form-control');
}
