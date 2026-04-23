// -*- coding: utf-8 -*-
// Electron主进程 - 简化架构（JSON文件读取）
// 架构: Python分析引擎 → JSON文件 → Electron前端读取
// 版本: v3.2 - 后台异步更新 + 刷新按钮更新

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn, exec } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let isUpdating = false;

const PYTHON_SCRIPT = 'e:\\csi10\\analyzer_json_v3.1.py';
const JSON_FILE = 'e:\\csi10\\result.json';
const PYTHON_EXE = 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe';
const DATA_FETCHER = 'e:\\csi10\\data_fetcher.py';

// 后台异步更新数据（只更新股票池30只股票）
function updateDataInBackground() {
  if (isUpdating) {
    console.log('数据更新进行中，跳过...');
    return;
  }
  
  isUpdating = true;
  console.log('\n========================================');
  console.log('后台异步更新数据（股票池30只）');
  console.log('========================================\n');
  
  // 异步运行数据更新脚本
  const updateProcess = spawn(PYTHON_EXE, [DATA_FETCHER], {
    cwd: path.dirname(DATA_FETCHER),
    detached: false
  });
  
  updateProcess.stdout.on('data', (data) => {
    console.log(`[数据更新] ${data.toString().trim()}`);
  });
  
  updateProcess.stderr.on('data', (data) => {
    console.error(`[数据更新错误] ${data.toString().trim()}`);
  });
  
  updateProcess.on('close', (code) => {
    console.log(`数据更新完成，退出码: ${code}`);
    isUpdating = false;
    
    // 数据更新完成后，重新运行分析引擎
    console.log('重新运行分析引擎...');
    runAnalyzerInBackground();
  });
}

// 后台异步运行分析引擎
function runAnalyzerInBackground() {
  console.log('运行分析引擎（完整43特征）...');
  
  const analyzerProcess = spawn(PYTHON_EXE, [PYTHON_SCRIPT], {
    cwd: path.dirname(PYTHON_SCRIPT),
    detached: false
  });
  
  analyzerProcess.stdout.on('data', (data) => {
    console.log(`[分析引擎] ${data.toString().trim()}`);
  });
  
  analyzerProcess.stderr.on('data', (data) => {
    console.error(`[分析引擎错误] ${data.toString().trim()}`);
  });
  
  analyzerProcess.on('close', (code) => {
    console.log(`分析完成，退出码: ${code}`);
    
    // 分析完成后，通知前端刷新
    if (mainWindow) {
      mainWindow.webContents.send('data-updated');
      console.log('已通知前端刷新数据');
    }
  });
}

// 同步刷新数据（刷新按钮点击时）
function refreshDataSync() {
  console.log('\n========================================');
  console.log('刷新按钮触发：更新数据 + 重新分析');
  console.log('========================================\n');
  
  // 同步更新数据
  try {
    exec(PYTHON_EXE + ' "' + DATA_FETCHER + '"', {
      cwd: path.dirname(DATA_FETCHER),
      encoding: 'utf8',
      timeout: 120000
    });
    console.log('✓ 数据更新完成');
  } catch (e) {
    console.log('数据更新提示:', e.stdout || e.message);
  }
  
  // 同步运行分析引擎
  try {
    exec(PYTHON_EXE + ' "' + PYTHON_SCRIPT + '"', {
      cwd: path.dirname(PYTHON_SCRIPT),
      encoding: 'utf8',
      timeout: 120000
    });
    console.log('✓ 分析完成');
    
    const data = readJSON();
    return { status: 'success', time: data ? data.update_time : '未知' };
  } catch (e) {
    console.error('分析失败:', e.message);
    return { status: 'failed', error: e.message };
  }
}

// 读取JSON文件
function readJSON() {
  try {
    if (fs.existsSync(JSON_FILE)) {
      const data = fs.readFileSync(JSON_FILE, 'utf8');
      return JSON.parse(data);
    }
    return null;
  } catch (e) {
    console.error('读取JSON失败:', e.message);
    return null;
  }
}

// 创建窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    },
    title: '波段股票分析系统 v3.2 (后台更新)'
  });
  
  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  
  // 窗口创建后，立即启动后台数据更新
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('\n窗口加载完成，启动后台数据更新...');
    updateDataInBackground();
  });
}

// IPC Handlers
ipcMain.handle('get-all-stocks', () => {
  const data = readJSON();
  return data ? data.stocks : [];
});

ipcMain.handle('get-buy-stocks', () => {
  const data = readJSON();
  return data ? data.buy : [];
});

ipcMain.handle('get-sell-stocks', () => {
  const data = readJSON();
  return data ? data.sell : [];
});

ipcMain.handle('get-status', () => {
  const data = readJSON();
  return data || {
    update_time: '未更新',
    stock_count: 0,
    buy_count: 0,
    sell_count: 0,
    avg_accuracy: 0
  };
});

ipcMain.handle('refresh-data', () => {
  // 刷新按钮触发：同步更新数据 + 重新分析
  return refreshDataSync();
});

// 启动流程（先显示界面，后台更新数据）
app.whenReady().then(() => {
  console.log('\n========================================');
  console.log('波段股票分析系统启动 v3.2');
  console.log('最高原则: 准确性第一');
  console.log('启动流程: 先显示界面 → 后台异步更新数据');
  console.log('========================================\n');
  
  // 先创建窗口显示界面（使用现有JSON数据）
  createWindow();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});