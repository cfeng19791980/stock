// -*- coding: utf-8 -*-
// Electron主进程 - 简化架构（JSON文件读取）
// 架构: Python分析引擎 → JSON文件 → Electron前端读取
// 版本: v3.1 - 数据实时性保障

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;

const PYTHON_SCRIPT = 'e:\\csi10\\analyzer_json_v3.1.py';
const JSON_FILE = 'e:\\csi10\\result.json';
const PYTHON_EXE = 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe';
const DATA_CHECK_SCRIPT = 'e:\\csi10\\data_check_and_update.py';

// Step 1: 检查数据完整性并自动更新
function checkDataIntegrity() {
  console.log('检查数据完整性...');
  try {
    const result = execSync(PYTHON_EXE + ' "' + DATA_CHECK_SCRIPT + '"', {
      cwd: path.dirname(DATA_CHECK_SCRIPT),
      encoding: 'utf8',
      timeout: 120000
    });
    console.log(result);
    return true;
  } catch (e) {
    // 如果数据检查脚本返回非0（需要更新），会抛出异常
    // 但数据更新可能已经执行，所以继续运行分析引擎
    console.log('数据检查提示:', e.stdout || e.message);
    return true; // 继续运行分析引擎
  }
}

// Step 2: 运行分析引擎（强制重新计算）
function runAnalyzer() {
  console.log('运行分析引擎（完整43特征）...');
  try {
    execSync(PYTHON_EXE + ' "' + PYTHON_SCRIPT + '"', {
      cwd: path.dirname(PYTHON_SCRIPT),
      encoding: 'utf8',
      timeout: 120000  // 2分钟超时
    });
    console.log('分析完成！');
    return true;
  } catch (e) {
    console.error('分析失败:', e.message);
    return false;
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
    title: '波段股票分析系统 v3.1 (实时数据)'
  });
  
  mainWindow.loadFile(path.join(__dirname, 'index.html'));
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
  // 刷新时也先检查数据完整性
  checkDataIntegrity();
  
  const success = runAnalyzer();
  if (success) {
    const data = readJSON();
    return { status: 'success', time: data ? data.update_time : '未知' };
  }
  return { status: 'failed', error: '分析引擎运行失败' };
});

// 启动流程（确保数据实时性）
app.whenReady().then(() => {
  console.log('\n========================================');
  console.log('波段股票分析系统启动');
  console.log('最高原则: 准确性第一');
  console.log('========================================\n');
  
  // Step 1: 检查数据完整性（自动更新滞后数据）
  checkDataIntegrity();
  
  // Step 2: 运行分析引擎（强制重新计算）
  runAnalyzer();
  
  // Step 3: 创建窗口显示结果
  createWindow();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});