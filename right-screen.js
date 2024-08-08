window.addEventListener('message', function(event) {
    if (event.data.type === 'updateInfo') {
        document.getElementById('infoDisplay').textContent = event.data.content;
    }
});