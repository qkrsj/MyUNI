import { powerMonitor } from 'electron';
import {
  RULES,
  dayKey,
  emptyInteractions,
  expToNextLevel,
  totalExpForLevel,
  type InteractionCounts,
  type InteractionKind,
  type Me,
} from '@myuni/shared';
import type { PetEvent, PetView } from '../ipc';
import { ApiError, api } from './api';

const TICK_MS = 60_000;
const SYNC_EVERY_TICKS = 5;
const INTERACTION_SYNC_DELAY_MS = 2_000;

export interface GameCallbacks {
  onView(view: PetView): void;
  onEvent(event: PetEvent): void;
  onMeChanged(me: Me): void;
  onUnauthorized(): void;
}

/**
 * 클라이언트 쪽 게임 루프.
 * - 1분마다 자리 비움 여부를 확인해 활동 시간을 쌓는다.
 * - 쌓인 활동/상호작용을 주기적으로 서버에 보내고, 서버가 계산한 결과로 상태를 갱신한다.
 * 경험치의 최종 판정은 항상 서버가 한다. 여기서의 제한 확인은 즉각적인 반응을 위한 것.
 */
export class GameSession {
  private pending = { activeMinutes: 0, interactions: emptyInteractions() };
  private ticks = 0;
  private sleeping = false;
  private syncing = false;
  private lastSyncDay = dayKey();
  private tickTimer?: NodeJS.Timeout;
  private syncTimer?: NodeJS.Timeout;

  constructor(
    private token: string,
    private me: Me,
    private readonly cb: GameCallbacks,
  ) {}

  start(): void {
    this.tickTimer = setInterval(() => this.tick(), TICK_MS);
    this.emitView();
    void this.sync();
  }

  async stop(): Promise<void> {
    clearInterval(this.tickTimer);
    clearTimeout(this.syncTimer);
    await this.sync();
  }

  /** 오늘 해당 상호작용을 더 할 수 있는지 (서버 기록 + 아직 안 보낸 것) */
  usedToday(kind: InteractionKind): number {
    const serverCount = this.lastSyncDay === dayKey() ? this.me.today.interactions[kind] : 0;
    return serverCount + this.pending.interactions[kind];
  }

  interact(kind: InteractionKind): void {
    if (this.usedToday(kind) >= RULES.interactions[kind].dailyLimit) {
      this.cb.onEvent({ type: 'limit', kind });
      return;
    }
    this.pending.interactions[kind]++;
    this.cb.onEvent({ type: 'interacted', kind });
    clearTimeout(this.syncTimer);
    this.syncTimer = setTimeout(() => void this.sync(), INTERACTION_SYNC_DELAY_MS);
  }

  view(): PetView {
    const { level, totalExp, evolutionStage } = this.me.character;
    const inLevel = totalExp - totalExpForLevel(level);
    return {
      nickname: this.me.nickname,
      level,
      evolutionStage,
      levelProgress: Math.min(1, inLevel / expToNextLevel(level)),
      todayExp: this.lastSyncDay === dayKey() ? this.me.today.exp : 0,
      dailyExpCap: RULES.dailyExpCap,
      ranked: this.me.ranked,
      sleeping: this.sleeping,
      animal: this.me.school?.animal ?? 'duck',
      colorPrimary: this.me.school?.colorPrimary ?? '#F4C430',
      colorSecondary: this.me.school?.colorSecondary ?? '#FFFFFF',
      schoolName: this.me.school?.name ?? null,
    };
  }

  private tick(): void {
    const idle = powerMonitor.getSystemIdleTime() >= RULES.idleThresholdSec;
    if (!idle) this.pending.activeMinutes++;
    if (idle !== this.sleeping) {
      this.sleeping = idle;
      this.emitView();
    }
    if (++this.ticks % SYNC_EVERY_TICKS === 0) void this.sync();
  }

  private async sync(): Promise<void> {
    if (this.syncing) return;
    const batch = this.pending;
    const hasWork = batch.activeMinutes > 0 || Object.values(batch.interactions).some((n) => n > 0);
    if (!hasWork && this.lastSyncDay === dayKey()) return;

    this.syncing = true;
    this.pending = { activeMinutes: 0, interactions: emptyInteractions() };
    try {
      const day = dayKey();
      const res = await api.sync(this.token, batch);
      this.applyMe(res.me);
      this.lastSyncDay = day;
    } catch (err) {
      // 실패하면 다음 동기화 때 다시 보낸다
      this.pending.activeMinutes += batch.activeMinutes;
      for (const k of Object.keys(batch.interactions) as InteractionKind[]) {
        (this.pending.interactions as InteractionCounts)[k] += batch.interactions[k];
      }
      if (err instanceof ApiError && err.status === 401) this.cb.onUnauthorized();
    } finally {
      this.syncing = false;
    }
  }

  private applyMe(next: Me): void {
    const prev = this.me.character;
    this.me = next;
    if (next.character.level > prev.level) this.cb.onEvent({ type: 'levelUp', level: next.character.level });
    if (next.character.evolutionStage > prev.evolutionStage) {
      this.cb.onEvent({ type: 'evolved', stage: next.character.evolutionStage });
    }
    this.cb.onMeChanged(next);
    this.emitView();
  }

  private emitView(): void {
    this.cb.onView(this.view());
  }
}
