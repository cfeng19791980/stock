// 最简测试版
const { app, BrowserWindow } = require('electron');
const path = require('path');

console.log('[TEST] __dirname:', __dirname);
console.log('[TEST] index.html:', path.join(__dirname, 'index.html'));

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  
  console.log('[TEST] 加载:', path.join(__dirname, 'index.html'));
  win.loadFile(path.join(__dirname, 'index.html'));
  win.webContents.openDevTools();
}

app.whenReady().then(() => {
  console.log('[TEST] App ready');
  createWindow();
});

app.on('window-all-closed', () => app.quit());