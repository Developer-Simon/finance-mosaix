const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('financeMosaix', {
  platform: process.platform,
});
