// -*- coding: utf-8 -*-
// Electron预加载脚本 - v4.0 持仓管理版

const { contextBridge, ipcRenderer } = require('electron');

// 暴露API给渲染进程
contextBridge.exposeInMainWorld('stockAPI', {
  getAll: () => ipcRenderer.invoke('get-all-stocks'),
  getBuy: () => ipcRenderer.invoke('get-buy-stocks'),
  getSell: () => ipcRenderer.invoke('get-sell-stocks'),
  getStatus: () => ipcRenderer.invoke('get-status'),
  refresh: () => ipcRenderer.invoke('refresh-data'),
  getHoldings: () => ipcRenderer.invoke('get-holdings'),
  saveHoldings: (holdings) => ipcRenderer.invoke('save-holdings', holdings),
  getUpdateStatus: () => ipcRenderer.invoke('get-update-status'),
  platform: process.platform
});

// 暴露electronAPI给加载页面
contextBridge.exposeInMainWorld('electronAPI', {
  onBackendProgress: (callback) => ipcRenderer.on('backend-progress', (e, msg) => callback(msg)),
  onBackendReady: (callback) => ipcRenderer.on('backend-ready', () => callback()),
  onBackendError: (callback) => ipcRenderer.on('backend-error', (e, err) => callback(err)),
  onDataUpdated: (callback) => ipcRenderer.on('data-updated', () => callback()),
  onUpdateStatus: (callback) => ipcRenderer.on('update-status', (e, status) => callback(status)),
  refreshData: () => ipcRenderer.invoke('refresh-data'),
  checkBackend: () => ipcRenderer.invoke('check-backend'),
  getHoldings: () => ipcRenderer.invoke('get-holdings'),
  saveHoldings: (holdings) => ipcRenderer.invoke('save-holdings', holdings),
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('backend-progress');
    ipcRenderer.removeAllListeners('backend-ready');
    ipcRenderer.removeAllListeners('backend-error');
    ipcRenderer.removeAllListeners('data-updated');
    ipcRenderer.removeAllListeners('update-status');
  }
});