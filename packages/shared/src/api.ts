import { z } from 'zod';
import { INTERACTION_KINDS, type InteractionKind } from './rules.js';

export const nicknameSchema = z
  .string()
  .trim()
  .min(2)
  .max(16)
  .regex(/^[0-9A-Za-z가-힣_]+$/, '한글, 영문, 숫자, _ 만 사용할 수 있어요');

export const passwordSchema = z.string().min(8).max(72);

/** 클라이언트가 보내는 기기 식별값: SHA-256(원본 기기 ID) 16진수. 원본은 기기 밖으로 나가지 않는다. */
export const deviceIdSchema = z.string().regex(/^[0-9a-f]{64}$/);

export const signupRequest = z.object({
  nickname: nicknameSchema,
  password: passwordSchema,
  schoolId: z.number().int().positive().nullable(),
  deviceId: deviceIdSchema,
});
export type SignupRequest = z.infer<typeof signupRequest>;

export const loginRequest = z.object({
  nickname: nicknameSchema,
  password: z.string().min(1).max(72),
  deviceId: deviceIdSchema,
});
export type LoginRequest = z.infer<typeof loginRequest>;

export const changeSchoolRequest = z.object({
  schoolId: z.number().int().positive(),
});

const interactionShape = Object.fromEntries(
  INTERACTION_KINDS.map((k) => [k, z.number().int().min(0).max(1000).optional()]),
) as Record<InteractionKind, z.ZodOptional<z.ZodNumber>>;

export const syncRequest = z.object({
  activeMinutes: z.number().int().min(0).max(24 * 60),
  interactions: z.object(interactionShape),
});
export type SyncRequest = z.infer<typeof syncRequest>;

export interface School {
  id: number;
  name: string;
  animal: string;
  colorPrimary: string;
  colorSecondary: string;
  spriteSet: string;
}

export interface CharacterState {
  level: number;
  totalExp: number;
  evolutionStage: number;
}

export interface Me {
  id: number;
  nickname: string;
  school: School | null;
  schoolChangedAt: string | null;
  /** 이 계정이 랭킹에 반영되는지 (기기당 1계정) */
  ranked: boolean;
  character: CharacterState;
  today: { exp: number; interactions: Record<InteractionKind, number> };
}

export interface AuthResponse {
  token: string;
  me: Me;
}

export interface SyncResponse {
  granted: number;
  me: Me;
}

export interface SchoolRankingEntry {
  rank: number;
  school: Pick<School, 'id' | 'name' | 'animal'>;
  score: number;
  members: number;
}

export interface UserRankingEntry {
  rank: number;
  nickname: string;
  schoolName: string | null;
  score: number;
}
