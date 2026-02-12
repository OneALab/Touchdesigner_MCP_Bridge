let previewIntervals = [];

async function loadPreviews() {
    stopAllPreviews();
    const grid = document.getElementById('preview-grid');
    grid.innerHTML = '<p>Loading...</p>';
    try {
        const res = await fetch('/preview/discover', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
        const data = await res.json();
        if (!data.success) {
            grid.innerHTML = '<p>No previews found</p>';
            return;
        }
        grid.innerHTML = '';

        // TOPs section
        if (data.tops && data.tops.length > 0) {
            const topSection = document.createElement('div');
            topSection.innerHTML = '<h3 style="margin:1rem;color:var(--text-secondary);">TOPs</h3>';
            grid.appendChild(topSection);
            const topGrid = document.createElement('div');
            topGrid.className = 'preview-grid-inner';
            for (const top of data.tops) {
                createTopPreview(top, topGrid);
            }
            grid.appendChild(topGrid);
        }

        // CHOPs section
        if (data.chops && data.chops.length > 0) {
            const chopSection = document.createElement('div');
            chopSection.innerHTML = '<h3 style="margin:1rem;color:var(--text-secondary);">CHOPs</h3>';
            grid.appendChild(chopSection);
            const chopGrid = document.createElement('div');
            chopGrid.className = 'preview-grid-inner chop-grid';
            for (const chop of data.chops) {
                createChopPreview(chop, chopGrid);
            }
            grid.appendChild(chopGrid);
        }

        if ((!data.tops || data.tops.length === 0) && (!data.chops || data.chops.length === 0)) {
            grid.innerHTML = '<p>No TOPs or CHOPs found</p>';
        }
    } catch (e) {
        grid.innerHTML = '<p>Error loading previews: ' + e + '</p>';
    }
}

function createTopPreview(top, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'top-preview-wrapper';
    wrapper.innerHTML = '<div class="preview-label">' + top.name + '</div><img class="top-preview" src="/preview/top?path=' + encodeURIComponent(top.path) + '&t=' + Date.now() + '">';
    const img = wrapper.querySelector('img');
    const interval = setInterval(() => {
        img.src = '/preview/top?path=' + encodeURIComponent(top.path) + '&t=' + Date.now();
    }, 500);
    previewIntervals.push(interval);
    container.appendChild(wrapper);
}

function createChopPreview(chop, container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'chop-preview-wrapper';
    wrapper.innerHTML = '<div class="preview-label">' + chop.name + ' <span class="chop-type">(' + chop.type + ')</span></div><canvas class="chop-canvas" width="300" height="100"></canvas>';
    const canvas = wrapper.querySelector('canvas');
    const ctx = canvas.getContext('2d');
    const colors = ['#58a6ff', '#f85149', '#3fb950', '#d29922', '#a371f7', '#f778ba'];

    async function drawChop() {
        try {
            const res = await fetch('/preview/chop', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: chop.path, max_samples: 100})
            });
            const data = await res.json();
            if (!data.success || !data.channels) return;

            ctx.fillStyle = '#161b22';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            data.channels.forEach((ch, i) => {
                if (!ch.values || ch.values.length === 0) return;
                ctx.strokeStyle = colors[i % colors.length];
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                const range = (ch.max - ch.min) || 1;
                ch.values.forEach((v, x) => {
                    const px = (x / ch.values.length) * canvas.width;
                    const py = canvas.height - ((v - ch.min) / range) * canvas.height;
                    x === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                });
                ctx.stroke();
            });

            // Draw channel names
            ctx.font = '10px sans-serif';
            data.channels.forEach((ch, i) => {
                ctx.fillStyle = colors[i % colors.length];
                ctx.fillText(ch.name, 4, 12 + i * 12);
            });
        } catch (e) {
            ctx.fillStyle = '#f85149';
            ctx.fillText('Error', 10, 20);
        }
    }

    drawChop();
    const interval = setInterval(drawChop, 100);
    previewIntervals.push(interval);
    container.appendChild(wrapper);
}

function stopAllPreviews() {
    previewIntervals.forEach(i => clearInterval(i));
    previewIntervals = [];
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.querySelector('[data-tab="previews"]');
    if (btn) btn.addEventListener('click', loadPreviews);
});