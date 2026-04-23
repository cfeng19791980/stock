// -*- coding: utf-8 -*-
// Electron主进程 - 先启动窗口，后台启动Python服务

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow;
let pythonProcess;
let backendReady = false;

const PYTHON_SCRIPT = 'e:\\csi10\\final_v2_clean.py';
const PYTHON_EXE = 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe';

// 创建窗口（立即显示加载界面）
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    icon: path.join(__dirname, 'icon.png'),
    title: '波段股票分析系统 v2.2'
  });
  
  // 先加载加载页面
  mainWindow.loadFile(path.join(__dirname, 'loading.html'));
  
  // 开发模式下打开DevTools
  // mainWindow.webContents.openDevTools();
}

// 启动Python后端（后台运行）
function startPythonBackend() {
  console.log('后台启动Python服务...');
  
  pythonProcess = spawn(PYTHON_EXE, [PYTHON_SCRIPT], {
    cwd: path.dirname(PYTHON_SCRIPT),
    stdio: ['ignore', 'pipe', 'pipe']
  });
  
  pythonProcess.stdout.on('data', (data) => {
    const msg = data.toString();
    console.log(`Python: ${msg}`);
    
    // 发送进度更新到窗口
    if (mainWindow && !backendReady) {
      mainWindow.webContents.send('backend-progress', msg);
    }
  });
  
  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python Error: ${data.toString()}`);
  });
  
  pythonProcess.on('close', (code) => {
    console.log(`Python进程退出: ${code}`);
    backendReady = false;
  });
  
  // 开始检查后端就绪
  checkBackendReady();
}

// 检查后端是否就绪
function checkBackendReady() {
  let retries = 0;
  const maxRetries = 60; // 60秒等待
  
  function check() {
    http.get('http://localhost:5000/api/status', (res) => {
      if (res.statusCode === 200) {
        console.log('Backend ready!');
        backendReady = true;
        
        // 切换到主界面
        if (mainWindow) {
          mainWindow.loadFile(path.join(__dirname, 'index.html'));
          mainWindow.webContents.send('backend-ready');
        }
      }
    }).on('error', () => {
      retries++;
      if (retries < maxRetries) {
        console.log(`等待后端... (${retries}/${maxRetries})`);
        setTimeout(check, 1000);
      } else {
        console.log('后端启动超时');
        if (mainWindow) {
          mainWindow.webContents.send('backend-error', '后端启动超时，请手动刷新');
        }
      }
    });
  }
  
  check();
}

// 停止Python后端
function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// IPC处理器
ipcMain.handle('get-all-stocks', async () => {
  return await fetchAPI('http://localhost:5000/api/all');
});

ipcMain.handle('get-buy-stocks', async () => {
  return await fetchAPI('http://localhost:5000/api/buy');
});

ipcMain.handle('get-sell-stocks', async () => {
  return await fetchAPI('http://localhost:5000/api/sell');
});

ipcMain.handle('refresh-data', async () => {
  return await fetchAPI('http://localhost:5000/api/refresh');
});

ipcMain.handle('get-status', async () => {
  return await fetchAPI('http://localhost:5000/api/status');
});

ipcMain.handle('get-buysell', async (event, code) => {
  return await fetchAPI(`http://localhost:5000/api/buysell/${code}`);
});

ipcMain.handle('check-backend', async () => {
  return { ready: backendReady };
});

// HTTP请求函数
async function fetchAPI(url) {
  try {
    const http = require('http');
    return new Promise((resolve, reject) => {
      http.get(url, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(e);
          }
        });
      }).on('error', reject);
    });
  } catch (e) {
    return { error: e.message };
  }
}

// 应用启动 - 先创建窗口
app.whenReady().then(() => {
  // 1. 立即创建窗口（显示加载界面）
  createWindow();
  
  // 2. 后台启动Python服务
  setTimeout(startPythonBackend, 500);
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
      setTimeout(startPythonBackend, 500);
    }
  });
});

// 关闭所有窗口时退出
app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 应用退出时清理
app.on('before-quit', () => {
  stopPythonBackend();
});