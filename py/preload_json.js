// -*- coding: utf-8 -*-
// preload.js - IPC桥接（JSON文件读取架构）

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('stockAPI', {
  // 获取所有股票
  getAll: () => ipcRenderer.invoke('get-all-stocks'),
  
  // 获取买入推荐
  getBuy: () => ipcRenderer.invoke('get-buy-stocks'),
  
  // 获取卖出信号
  getSell: () => ipcRenderer.invoke('get-sell-stocks'),
  
  // 获取状态
  getStatus: () => ipcRenderer.invoke('get-status'),
  
  // 刷新数据
  refresh: () => ipcRenderer.invoke('refresh-data')
});