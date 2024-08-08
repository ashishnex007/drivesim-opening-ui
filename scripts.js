let leftWindow, rightWindow;

function deployScreens() {
    leftWindow = window.open('left.html', 'leftScreen', 'width=800,height=600');
    rightWindow = window.open('right.html', 'rightScreen', 'width=800,height=600');
    
    // Request full screen for all windows
    requestFullScreen(document.documentElement);
    leftWindow.addEventListener('load', () => requestFullScreen(leftWindow.document.documentElement));
    rightWindow.addEventListener('load', () => requestFullScreen(rightWindow.document.documentElement));
}

// Function to request full screen mode
function requestFullScreen(element) {
    if (element.requestFullscreen) {
        element.requestFullscreen();
    } else if (element.mozRequestFullScreen) { // Firefox
        element.mozRequestFullScreen();
    } else if (element.webkitRequestFullscreen) { // Chrome, Safari, and Opera
        element.webkitRequestFullscreen();
    } else if (element.msRequestFullscreen) { // IE/Edge
        element.msRequestFullscreen();
    }
}

function showFrame(frameId) {
    const frames = document.querySelectorAll('.frame');
    frames.forEach(frame => frame.style.display = 'none');
    document.getElementById(frameId).style.display = 'flex';

    // Send message to right screen
    if (rightWindow) {
        rightWindow.postMessage({ type: 'updateInfo', content: `Showing ${frameId}` }, '*');
    }
}

function closeApp() {
    window.close();
}

function runPracticeCommand() {
    fetch('run_script.php?action=runPracticeCommand', { method: 'GET' })
    .then(response => response.text())
    .then(data => console.log(data));
}

function openScenesPage(level) {
    const scenesFrame = document.getElementById('scenesFrame');
    scenesFrame.innerHTML = '';
    const wrapper = document.createElement('div');
    wrapper.className = 'flex flex-col w-1/2 items-center gap-y-8 justify-center';
    showFrame('scenesFrame');
    
    const scenes = ['Scene 1', 'Scene 2'];
    scenes.forEach(scene => {
        const button = document.createElement('button');
        button.innerText = scene;
        button.className = 'w-[10rem] bg-violet-500 text-lg hover:bg-violet-600 hover:w-[12rem] hover:px-6 hover:py-6 hover:text-2xl text-white font-bold py-4 px-4 rounded transition-all';
        button.onclick = () => openTownPage(level, scene);
        wrapper.appendChild(button);
    });
    
    const backButton = document.createElement('button');
    backButton.innerText = 'Back';
    backButton.className = 'w-[10rem] bg-blue-500 text-lg hover:bg-blue-600 hover:w-[12rem] hover:px-6 hover:py-6 hover:text-2xl text-white font-bold py-4 px-4 rounded transition-all';
    backButton.onclick = () => showFrame('levelFrame');
    wrapper.appendChild(backButton);

    scenesFrame.appendChild(wrapper);

    const heroImage = document.createElement('img');
    heroImage.src = 'hero.png';
    heroImage.className = 'h-[35rem] px-20';
    scenesFrame.appendChild(heroImage);

    if (rightWindow) {
        rightWindow.postMessage({ type: 'updateInfo', content: `Choosing ${level} difficulty` }, '*');
    }
}

function openTownPage(level, scene) {
    const townFrame = document.getElementById('townFrame');
    townFrame.innerHTML = '';
    const wrapper = document.createElement('div');
    wrapper.className = 'flex flex-col w-1/2 items-center gap-y-8 justify-center';
    showFrame('townFrame');
    
    const towns = ['Town 02', 'Town 03', 'Town 04', 'Town 05'];
    towns.forEach(town => {
        const button = document.createElement('button');
        button.innerText = town;
        button.className = 'w-[10rem] bg-teal-500 text-lg hover:bg-teal-600 hover:w-[12rem] hover:px-6 hover:py-6 hover:text-2xl text-white font-bold py-4 px-4 rounded transition-all';
        button.onclick = () => openTerminals(level, scene, town);
        wrapper.appendChild(button);
    });
    
    const backButton = document.createElement('button');
    backButton.innerText = 'Back';
    backButton.className = 'w-[10rem] bg-blue-500 text-lg hover:bg-blue-600 hover:w-[12rem] hover:px-6 hover:py-6 hover:text-2xl text-white font-bold py-4 px-4 rounded transition-all';
    backButton.onclick = () => openScenesPage(level);
    wrapper.appendChild(backButton);

    townFrame.appendChild(wrapper);

    const heroImage = document.createElement('img');
    heroImage.src = 'hero.png';
    heroImage.className = 'h-[35rem] px-20';
    townFrame.appendChild(heroImage);

    if (rightWindow) {
        rightWindow.postMessage({ type: 'updateInfo', content: `Choosing ${scene} in ${level} difficulty` }, '*');
    }
}

function openTerminals(level, scene, town) {
    fetch('PHP/run_script.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ level, scene, town })
    })
    .then(response => response.text())
    .then(data => console.log(data));  

    if (rightWindow) {
        rightWindow.postMessage({ type: 'updateInfo', content: `Opening ${town} in ${scene} (${level} difficulty)` }, '*');
    }
}

// Initially show the landing frame
showFrame('landingFrame');