let currentDays = 14;

document.addEventListener('DOMContentLoaded', function () {
    loadSchedule(currentDays);

    document.getElementById('days-select').addEventListener('change', function (e) {
        currentDays = parseInt(e.target.value);
        loadSchedule(currentDays);
    });

    document.getElementById('refresh-btn').addEventListener('click', function () {
        loadSchedule(currentDays);
    });
});

async function loadSchedule(days) {
    const loading = document.getElementById('loading');
    const container = document.getElementById('schedule-container');

    loading.style.display = 'block';
    container.style.display = 'none';

    try {
        const response = await fetch(`/api/schedule/${days}`);
        const data = await response.json();

        renderSchedule(data);

        loading.style.display = 'none';
        container.style.display = 'block';
    } catch (error) {
        console.error('Error loading schedule:', error);
        loading.textContent = 'Error loading schedule. Please refresh the page.';
    }
}

function renderSchedule(schedule) {
    const tbody = document.getElementById('schedule-body');
    tbody.innerHTML = '';

    schedule.forEach(day => {
        const row = document.createElement('tr');

        // Weekend highlight
        const dayName = day.DAY.toLowerCase();
        if (dayName === 'saturday' || dayName === 'sunday') {
            row.classList.add('weekend');
        }

        // DATE CELL
        const dateCell = document.createElement('td');
        dateCell.className = 'date-cell cursor-target';
        dateCell.textContent = day.DATE;
        row.appendChild(dateCell);

        // DAY CELL
        const dayCell = document.createElement('td');
        dayCell.className = 'day-cell cursor-target';
        dayCell.textContent = day.DAY;
        row.appendChild(dayCell);

        // PLAYER CELLS
        PLAYERS.forEach(player => {
            const cell = document.createElement('td');
            cell.className = 'status-cell cursor-target';

            const select = document.createElement('select');
            select.className = 'status-select cursor-target';
            select.dataset.date = day.DATE;
            select.dataset.player = player;

            const currentStatus = day[player] || '';

            // OPTIONS
            const options = [
                { value: '', label: '⚪ Not Set' },
                { value: 'AVAILABLE', label: '✅ Available' },
                { value: 'MAYBE', label: '❓ Maybe' },
                { value: 'UNAVAILABLE', label: '❌ Unavailable' }
            ];

            options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt.value;
                option.textContent = opt.label;
                if (currentStatus === opt.value) option.selected = true;
                select.appendChild(option);
            });

            select.addEventListener('change', handleStatusChange);

            cell.appendChild(select);
            row.appendChild(cell);
        });

        // RESULT CELL
        const resultCell = document.createElement('td');
        const result = day.RESULT || '...';

        resultCell.className = `result-cell cursor-target ${getResultClass(result)}`;
        resultCell.textContent = getResultEmoji(result) + ' ' + result;

        row.appendChild(resultCell);

        tbody.appendChild(row);
    });
}

async function handleStatusChange(e) {
    const select = e.target;
    const date = select.dataset.date;
    const player = select.dataset.player;
    const status = select.value;

    try {
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ date, player, status })
        });

        if (response.ok) {
            loadSchedule(currentDays);
        } else {
            alert('Error updating status. Please try again.');
        }
    } catch (error) {
        console.error('Error updating status:', error);
        alert('Error updating status. Please try again.');
    }
}

function getResultEmoji(result) {
    const emojiMap = {
        'SCHEDULED': '🎲',
        'POTENTIALLY': '🤔',
        'NOT SCHEDULED': '❌'
    };
    return emojiMap[result] || '⚪';
}

function getResultClass(result) {
    const classMap = {
        'SCHEDULED': 'scheduled',
        'POTENTIALLY': 'potential',
        'NOT SCHEDULED': 'not-scheduled'
    };
    return classMap[result] || '';
}
