import { BrowserWindow, Menu, app, ipcMain } from 'electron';
import { RULES, type AuthResponse, type InteractionKind } from '@myuni/shared';
import { IPC, type CredentialsInput, type PetEvent, type PetView, type Result, type SignupInput } from '../ipc';
import { ApiError, api } from './api';
import { deviceId } from './device';
import { GameSession } from './game';
import { clearSession, loadSession, saveSession, type StoredSession } from './session';
import { createLoginWindow, createPetWindow } from './windows';

let petWindow: BrowserWindow | null = null;
let loginWindow: BrowserWindow | null = null;
let game: GameSession | null = null;
let lastView: PetView | null = null;

if (!app.requestSingleInstanceLock()) app.quit();

app.on('second-instance', () => loginWindow?.focus());

// 데스크톱 펫이므로 독/작업 표시줄에 아이콘을 띄우지 않는다
app.dock?.hide();

// 펫 창을 닫아도 앱은 메뉴의 "종료"로만 끝낸다
app.on('window-all-closed', () => {});

app.whenReady().then(async () => {
  registerIpc();
  const session = await loadSession();
  if (!session) return showLogin();

  try {
    const me = await api.me(session.token);
    await startGame({ token: session.token, me });
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      await clearSession();
      return showLogin();
    }
    // 오프라인: 마지막 상태로 시작하고 나중에 동기화
    await startGame(session);
  }
});

app.on('before-quit', async (e) => {
  if (!game) return;
  e.preventDefault();
  const g = game;
  game = null;
  await g.stop().catch(() => {});
  app.quit();
});

function showLogin(): void {
  if (loginWindow) return loginWindow.focus();
  loginWindow = createLoginWindow();
  loginWindow.on('closed', () => {
    loginWindow = null;
    if (!game) app.quit();
  });
}

async function startGame(session: StoredSession): Promise<void> {
  await saveSession(session);
  game = new GameSession(session.token, session.me, {
    onView: (view) => {
      lastView = view;
      petWindow?.webContents.send(IPC.view, view);
    },
    onEvent: (event: PetEvent) => petWindow?.webContents.send(IPC.event, event),
    onMeChanged: (me) => void saveSession({ token: session.token, me }),
    onUnauthorized: () => void logout(),
  });
  petWindow = createPetWindow();
  petWindow.on('closed', () => (petWindow = null));
  game.start();
}

async function logout(): Promise<void> {
  const g = game;
  game = null;
  await g?.stop().catch(() => {});
  await clearSession();
  petWindow?.destroy();
  showLogin();
}

async function handleAuth(call: () => Promise<AuthResponse>): Promise<Result> {
  try {
    const res = await call();
    await startGame({ token: res.token, me: res.me });
    loginWindow?.destroy();
    return { ok: true };
  } catch (err) {
    return { ok: false, message: err instanceof Error ? err.message : '알 수 없는 오류' };
  }
}

function showPetMenu(): void {
  if (!game || !petWindow) return;
  const g = game;
  const label = (kind: InteractionKind, name: string) => {
    const left = RULES.interactions[kind].dailyLimit - g.usedToday(kind);
    return `${name} (오늘 ${Math.max(0, left)}번 남음)`;
  };
  const view = g.view();
  Menu.buildFromTemplate([
    { label: `${view.nickname} · Lv.${view.level}${view.schoolName ? ` · ${view.schoolName}` : ''}`, enabled: false },
    { label: `오늘 경험치 ${view.todayExp} / ${view.dailyExpCap}`, enabled: false },
    ...(view.ranked ? [] : [{ label: '이 기기의 랭킹 반영 계정이 아니에요', enabled: false }]),
    { type: 'separator' },
    { label: label('feed', '먹이 주기'), click: () => g.interact('feed') },
    { label: label('play', '놀아 주기'), click: () => g.interact('play') },
    { type: 'separator' },
    { label: '로그아웃', click: () => void logout() },
    { label: 'MyUNi 종료', click: () => app.quit() },
  ]).popup({ window: petWindow });
}

function registerIpc(): void {
  ipcMain.handle(IPC.schools, () => api.schools());

  ipcMain.handle(IPC.login, async (_e, input: CredentialsInput) =>
    handleAuth(async () => api.login({ ...input, deviceId: await deviceId() })),
  );

  ipcMain.handle(IPC.signup, async (_e, input: SignupInput) =>
    handleAuth(async () => api.signup({ ...input, deviceId: await deviceId() })),
  );

  ipcMain.on(IPC.petReady, (e) => {
    if (lastView) e.sender.send(IPC.view, lastView);
  });

  ipcMain.on(IPC.setInteractive, (_e, interactive: boolean) => {
    petWindow?.setIgnoreMouseEvents(!interactive, { forward: true });
  });

  ipcMain.on(IPC.openMenu, () => showPetMenu());
}
