/** 메인 ↔ 렌더러 사이에서 주고받는 타입. 런타임 코드 없이 타입만 둔다. */
import type { InteractionKind, School } from '@myuni/shared';

/** 펫 창이 그리는 데 필요한 정보 */
export interface PetView {
  nickname: string;
  level: number;
  evolutionStage: number;
  /** 현재 레벨 안에서의 진행도 0..1 */
  levelProgress: number;
  todayExp: number;
  dailyExpCap: number;
  ranked: boolean;
  /** 컴퓨터가 자리 비움 상태면 잠든다 */
  sleeping: boolean;
  animal: string;
  colorPrimary: string;
  colorSecondary: string;
  schoolName: string | null;
}

export type PetEvent =
  | { type: 'interacted'; kind: InteractionKind }
  | { type: 'limit'; kind: InteractionKind }
  | { type: 'levelUp'; level: number }
  | { type: 'evolved'; stage: number };

export type Result = { ok: true } | { ok: false; message: string };

export interface CredentialsInput {
  nickname: string;
  password: string;
}

export interface SignupInput extends CredentialsInput {
  schoolId: number | null;
}

/** preload 가 window.myuni 로 노출하는 API */
export interface MyuniBridge {
  // 로그인 창
  getSchools(): Promise<School[]>;
  login(input: CredentialsInput): Promise<Result>;
  signup(input: SignupInput): Promise<Result>;
  // 펫 창
  petReady(): void;
  setInteractive(interactive: boolean): void;
  openMenu(): void;
  onView(cb: (view: PetView) => void): void;
  onEvent(cb: (event: PetEvent) => void): void;
}

export const IPC = {
  schools: 'auth:schools',
  login: 'auth:login',
  signup: 'auth:signup',
  petReady: 'pet:ready',
  setInteractive: 'pet:set-interactive',
  openMenu: 'pet:menu',
  view: 'pet:view',
  event: 'pet:event',
} as const;
