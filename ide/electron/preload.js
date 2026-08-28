const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("intentos", {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    node: process.versions.node,
  },
});
