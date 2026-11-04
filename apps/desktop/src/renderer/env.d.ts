import type { MyuniBridge } from '../ipc';

declare global {
  interface Window {
    myuni: MyuniBridge;
  }
}

export {};
