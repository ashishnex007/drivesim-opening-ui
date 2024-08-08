const { app, BrowserWindow, screen } = require('electron');

let leftWindow, middleWindow, rightWindow;

function createWindows() {
    const displays = screen.getAllDisplays();

    if (displays.length < 3) {
        console.error('Not enough monitors detected. This setup requires 3 monitors.');
        return;
    }

    // Create the left window
    leftWindow = new BrowserWindow({
        x: displays[0].bounds.x,
        y: displays[0].bounds.y,
        width: displays[0].bounds.width,
        height: displays[0].bounds.height,
        fullscreen: true,
    });
    leftWindow.loadFile('left.html');

    // Create the middle window (main)
    middleWindow = new BrowserWindow({
        x: displays[1].bounds.x,
        y: displays[1].bounds.y,
        width: displays[1].bounds.width,
        height: displays[1].bounds.height,
        fullscreen: true,
    });
    middleWindow.loadFile('index.html');

    // Create the right window
    rightWindow = new BrowserWindow({
        x: displays[2].bounds.x,
        y: displays[2].bounds.y,
        width: displays[2].bounds.width,
        height: displays[2].bounds.height,
        fullscreen: true,
    });
    rightWindow.loadFile('right.html');

    // Handle spawning of the left and right windows from the main window
    middleWindow.webContents.on('did-finish-load', () => {
        middleWindow.webContents.executeJavaScript(`
            const leftWindow = require('electron').remote.getGlobal('leftWindow');
            const rightWindow = require('electron').remote.getGlobal('rightWindow');
            leftWindow.show();
            rightWindow.show();
        `);
    });
}

app.whenReady().then(() => {
    createWindows();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindows();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});