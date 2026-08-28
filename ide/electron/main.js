// IntentOS desktop shell (Electron)
const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const DEV_URL = process.env.INTENTOS_DEV_URL || "http://localhost:5173";
let backendProcess = null;

function startBackend() {
  // If the FastAPI backend is not already running on :8000, spawn it.
  const http = require("http");
  const probe = http.get({ host: "127.0.0.1", port: 8000, path: "/api/health", timeout: 1500 }, (res) => {
    res.resume();
    res.on("end", () => {
      if (res.statusCode !== 200) spawnBackend();
    });
  });
  probe.on("error", () => spawnBackend());
  probe.on("timeout", () => {
    probe.destroy();
    spawnBackend();
  });
}

function spawnBackend() {
  const backendDir = path.join(__dirname, "..", "..", "backend");
  const python = process.env.INTENTOS_PYTHON || "python";
  backendProcess = spawn(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], {
    cwd: backendDir,
    stdio: "ignore",
    detached: true,
  });
  backendProcess.unref();
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1480,
    height: 920,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: "#070a12",
    titleBarStyle: "hiddenInset",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const isDev = process.env.NODE_ENV !== "production";
  if (isDev) {
    win.loadURL(DEV_URL);
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("quit", () => {
  if (backendProcess) {
    try {
      backendProcess.kill();
    } catch {
      /* already exited */
    }
  }
});
