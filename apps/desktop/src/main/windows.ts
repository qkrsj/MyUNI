import { BrowserWindow, screen } from 'electron';
import { join } from 'node:path';

const PET_WINDOW_HEIGHT = 140;

function loadPage(win: BrowserWindow, page: 'pet' | 'login'): void {
  const devUrl = process.env.ELECTRON_RENDERER_URL;
  if (devUrl) void win.loadURL(`${devUrl}/${page}.html`);
  else void win.loadFile(join(__dirname, `../renderer/${page}.html`));
}

const preload = () => join(__dirname, '../preload/index.js');

/**
 * 표시 층 (1차): 주 모니터 작업 영역 맨 아래에 붙는 투명·클릭 통과 창.
 * 캐릭터 위에 마우스가 올라갔을 때만 렌더러가 클릭을 받도록 전환한다.
 * 나중에 위젯/트레이 방식으로 바꿀 때는 이 함수와 renderer/pet.* 만 교체하면 된다.
 */
export function createPetWindow(): BrowserWindow {
  const win = new BrowserWindow({
    ...petBounds(),
    transparent: true,
    backgroundColor: '#00000000',
    frame: false,
    resizable: false,
    movable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    hasShadow: false,
    alwaysOnTop: true,
    show: false,
    webPreferences: { preload: preload(), sandbox: true, contextIsolation: true },
  });

  win.setAlwaysOnTop(true, 'floating');
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: false });
  win.setIgnoreMouseEvents(true, { forward: true });
  win.once('ready-to-show', () => win.showInactive());

  const reposition = () => {
    if (!win.isDestroyed()) win.setBounds(petBounds());
  };
  screen.on('display-metrics-changed', reposition);
  screen.on('display-added', reposition);
  screen.on('display-removed', reposition);
  win.on('closed', () => {
    screen.off('display-metrics-changed', reposition);
    screen.off('display-added', reposition);
    screen.off('display-removed', reposition);
  });

  loadPage(win, 'pet');
  return win;
}

function petBounds() {
  const { workArea } = screen.getPrimaryDisplay();
  return {
    x: workArea.x,
    y: workArea.y + workArea.height - PET_WINDOW_HEIGHT,
    width: workArea.width,
    height: PET_WINDOW_HEIGHT,
  };
}

export function createLoginWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 380,
    height: 560,
    resizable: false,
    title: 'MyUNi',
    autoHideMenuBar: true,
    show: false,
    webPreferences: { preload: preload(), sandbox: true, contextIsolation: true },
  });
  win.once('ready-to-show', () => win.show());
  loadPage(win, 'login');
  return win;
}
