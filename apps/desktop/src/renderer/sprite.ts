/**
 * 캐릭터 그리기. 지금은 아트가 없어서 도형으로 그리는 임시 렌더러.
 * 나중에 학교별 스프라이트 시트(spriteSet)가 생기면 같은 시그니처로 교체한다.
 * 학교 공식 마스코트가 아닌, 상징 동물 + 상징색 기반의 오리지널 캐릭터.
 */
export interface SpriteParams {
  animal: string;
  stage: number;
  colorPrimary: string;
  colorSecondary: string;
  /** 0..1 반복 애니메이션 진행도 */
  phase: number;
  facing: 1 | -1;
  pose: 'walk' | 'stand' | 'sleep' | 'jump';
}

/** 진화 단계별 크기 (px) */
export const STAGE_SIZE = [34, 40, 52, 64] as const;

export function spriteSize(stage: number): number {
  return STAGE_SIZE[Math.min(stage, STAGE_SIZE.length - 1)] ?? 40;
}

/** (x, groundY) 는 캐릭터 발 아래 중앙 */
export function drawPet(ctx: CanvasRenderingContext2D, x: number, groundY: number, p: SpriteParams): void {
  const size = spriteSize(p.stage);
  ctx.save();
  ctx.translate(x, groundY);
  ctx.scale(p.facing, 1);

  // 그림자
  ctx.fillStyle = 'rgba(0,0,0,0.18)';
  ctx.beginPath();
  ctx.ellipse(0, -2, size * 0.4, 4, 0, 0, Math.PI * 2);
  ctx.fill();

  if (p.stage === 0) drawEgg(ctx, size, p);
  else drawCreature(ctx, size, p);

  ctx.restore();
}

function drawEgg(ctx: CanvasRenderingContext2D, size: number, p: SpriteParams): void {
  const wobble = p.pose === 'sleep' ? 0 : Math.sin(p.phase * Math.PI * 2) * 0.12;
  const hop = p.pose === 'jump' ? 10 : 0;
  ctx.translate(0, -hop);
  ctx.rotate(wobble);
  ctx.fillStyle = p.colorSecondary;
  ctx.strokeStyle = shade(p.colorPrimary, -0.2);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(0, -size * 0.55, size * 0.38, size * 0.5, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  // 학교색 무늬
  ctx.fillStyle = p.colorPrimary;
  for (const [dx, dy, r] of [
    [-0.12, -0.7, 0.09],
    [0.14, -0.45, 0.07],
    [-0.05, -0.3, 0.05],
  ] as const) {
    ctx.beginPath();
    ctx.arc(dx * size, dy * size, r * size, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawCreature(ctx: CanvasRenderingContext2D, size: number, p: SpriteParams): void {
  const t = p.phase * Math.PI * 2;
  const walking = p.pose === 'walk';
  const bob = walking ? Math.abs(Math.sin(t)) * 3 : p.pose === 'sleep' ? Math.sin(t) * 1 : 0;
  const hop = p.pose === 'jump' ? 14 : 0;
  const bodyR = size * 0.42;
  const cy = -bodyR - 6 - bob - hop;
  const outline = shade(p.colorPrimary, -0.35);

  // 다리
  ctx.strokeStyle = outline;
  ctx.lineWidth = Math.max(2, size * 0.07);
  ctx.lineCap = 'round';
  const legSwing = walking ? Math.sin(t) * 4 : 0;
  for (const side of [-1, 1]) {
    ctx.beginPath();
    ctx.moveTo(side * bodyR * 0.4, cy + bodyR * 0.8);
    ctx.lineTo(side * bodyR * 0.4 + legSwing * side, -2 - hop);
    ctx.stroke();
  }

  // 동물별 머리 장식 (귀/깃털 등)
  ctx.fillStyle = p.colorPrimary;
  ctx.strokeStyle = outline;
  ctx.lineWidth = 2;
  drawFeature(ctx, p.animal, bodyR, cy);

  // 몸통
  ctx.beginPath();
  ctx.arc(0, cy, bodyR, 0, Math.PI * 2);
  ctx.fillStyle = p.colorPrimary;
  ctx.fill();
  ctx.stroke();

  // 배
  ctx.beginPath();
  ctx.ellipse(bodyR * 0.1, cy + bodyR * 0.42, bodyR * 0.52, bodyR * 0.42, 0, 0, Math.PI * 2);
  ctx.fillStyle = p.colorSecondary;
  ctx.fill();

  if (p.animal === 'tiger') {
    ctx.strokeStyle = outline;
    ctx.lineWidth = 2;
    for (const a of [-0.5, 0, 0.5]) {
      ctx.beginPath();
      ctx.moveTo(Math.sin(a) * bodyR * 0.9 - 4, cy - bodyR * 0.75);
      ctx.lineTo(Math.sin(a) * bodyR * 0.9, cy - bodyR * 0.45);
      ctx.stroke();
    }
  }

  // 눈
  const eyeX = bodyR * 0.35;
  const eyeY = cy - bodyR * 0.3;
  const dark = isDark(p.colorPrimary);
  ctx.strokeStyle = dark ? '#fff' : '#222';
  ctx.fillStyle = dark ? '#fff' : '#222';
  ctx.lineWidth = 2;
  if (p.pose === 'sleep') {
    for (const ex of [eyeX - bodyR * 0.3, eyeX + bodyR * 0.2]) {
      ctx.beginPath();
      ctx.moveTo(ex - 3, eyeY);
      ctx.lineTo(ex + 3, eyeY);
      ctx.stroke();
    }
  } else {
    for (const ex of [eyeX - bodyR * 0.3, eyeX + bodyR * 0.2]) {
      ctx.beginPath();
      ctx.arc(ex, eyeY, Math.max(2, size * 0.045), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // 부리/코
  if (p.animal === 'eagle' || p.animal === 'duck') {
    ctx.fillStyle = '#F5A623';
    ctx.beginPath();
    ctx.moveTo(bodyR * 0.75, cy - bodyR * 0.05);
    ctx.lineTo(bodyR * 1.15, cy + bodyR * 0.05);
    ctx.lineTo(bodyR * 0.75, cy + bodyR * 0.2);
    ctx.closePath();
    ctx.fill();
  } else {
    ctx.fillStyle = '#333';
    ctx.beginPath();
    ctx.arc(bodyR * 0.62, cy + bodyR * 0.08, 2.5, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawFeature(ctx: CanvasRenderingContext2D, animal: string, r: number, cy: number): void {
  switch (animal) {
    case 'eagle':
    case 'duck': {
      // 머리 깃털
      for (const dx of [-0.15, 0.1]) {
        ctx.beginPath();
        ctx.ellipse(dx * r, cy - r * 0.95, r * 0.12, r * 0.28, dx * 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      break;
    }
    default: {
      // 둥근 귀 (호랑이, 곰, 기타 포유류)
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.arc(side * r * 0.6, cy - r * 0.75, r * 0.28, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
    }
  }
}

function isDark(hex: string): boolean {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) return false;
  const n = parseInt(m[1]!, 16);
  const luma = 0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255);
  return luma < 110;
}

/** #RRGGBB 색을 밝게(+)/어둡게(-) */
export function shade(hex: string, amount: number): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) return hex;
  const n = parseInt(m[1]!, 16);
  const channel = (c: number) =>
    Math.round(Math.min(255, Math.max(0, amount < 0 ? c * (1 + amount) : c + (255 - c) * amount)));
  const r = channel((n >> 16) & 255);
  const g = channel((n >> 8) & 255);
  const b = channel(n & 255);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}
