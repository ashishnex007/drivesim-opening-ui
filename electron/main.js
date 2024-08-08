const { app, BrowserWindow, screen } = require('electron');

let mainWindow;

function createWindows() {
    const displays = screen.getAllDisplays();

    if (displays.length < 3) {
        console.error('This application requires at least three monitors.');
        app.quit();
        return;
    }

    // Create the main window spanning across all three monitors
    mainWindow = new BrowserWindow({
        width: 5760,
        height: 1920,
        x: 0,
        y: 0,
        webPreferences: {
            nodeIntegration: true,
        },
    });

    mainWindow.loadFile('index.html');
}

app.on('ready', createWindows);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindows();
    }
});