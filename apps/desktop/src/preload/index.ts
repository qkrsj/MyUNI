import { contextBridge, ipcRenderer } from 'electron';
import { IPC, type MyuniBridge, type PetEvent, type PetView } from '../ipc';

const bridge: MyuniBridge = {
  getSchools: () => ipcRenderer.invoke(IPC.schools),
  login: (input) => ipcRenderer.invoke(IPC.login, input),
  signup: (input) => ipcRenderer.invoke(IPC.signup, input),
  petReady: () => ipcRenderer.send(IPC.petReady),
  setInteractive: (interactive) => ipcRenderer.send(IPC.setInteractive, interactive),
  openMenu: () => ipcRenderer.send(IPC.openMenu),
  onView: (cb) => ipcRenderer.on(IPC.view, (_e, view: PetView) => cb(view)),
  onEvent: (cb) => ipcRenderer.on(IPC.event, (_e, event: PetEvent) => cb(event)),
};

contextBridge.exposeInMainWorld('myuni', bridge);
