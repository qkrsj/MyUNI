import type { PetEvent, PetView } from '../ipc';
import { drawPet, spriteSize } from './sprite';

const canvas = document.getElementById('stage') as HTMLCanvasElement;
const ctx = canvas.getContext('2d')!;
const bridge = window.myuni;

const WALK_SPEED = 38; // px/s
const GROUND_OFFSET = 4;

let view: PetView | null = null;

const pet = {
  x: 200,
  facing: 1 as 1 | -1,
  mode: 'stand' as 'walk' | 'stand',
  modeUntil: 0,
  jumpUntil: 0,
  phase: 0,
};

let hovering = false;
let interactive = false;
let bubble: { text: string; until: number } | null = null;
const hearts: { x: number; y: number; born: number }[] = [];

// ---------- 캔버스 ----------

function resize(): void {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(window.innerWidth * dpr);
  canvas.height = Math.round(window.innerHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  pet.x = Math.min(Math.max(pet.x, 40), window.innerWidth - 40);
}
window.addEventListener('resize', resize);
resize();

// ---------- 행동 ----------

function chooseNextMode(now: number): void {
  if (pet.mode === 'walk') {
    pet.mode = 'stand';
    pet.modeUntil = now + 2000 + Math.random() * 4000;
  } else {
    pet.mode = 'walk';
    if (Math.random() < 0.4) pet.facing = pet.facing === 1 ? -1 : 1;
    pet.modeUntil = now + 3000 + Math.random() * 6000;
  }
}

function update(dt: number, now: number): void {
  const sleeping = view?.sleeping ?? false;
  const isEgg = (view?.evolutionStage ?? 0) === 0;
  pet.phase = (pet.phase + dt * (pet.mode === 'walk' ? 1.6 : 0.5)) % 1;

  if (sleeping || hovering) return;
  if (now > pet.modeUntil) chooseNextMode(now);

  if (pet.mode === 'walk') {
    const speed = isEgg ? WALK_SPEED * 0.4 : WALK_SPEED;
    pet.x += pet.facing * speed * dt;
    const margin = 40;
    if (pet.x < margin) {
      pet.x = margin;
      pet.facing = 1;
    } else if (pet.x > window.innerWidth - margin) {
      pet.x = window.innerWidth - margin;
      pet.facing = -1;
    }
  }
}

// ---------- 그리기 ----------

function groundY(): number {
  return window.innerHeight - GROUND_OFFSET;
}

function petBox() {
  const size = spriteSize(view?.evolutionStage ?? 0);
  return { left: pet.x - size * 0.6, right: pet.x + size * 0.6, top: groundY() - size * 1.2 - 16, bottom: groundY() };
}

function render(now: number): void {
  ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
  if (!view) return;

  const pose = now < pet.jumpUntil ? 'jump' : view.sleeping ? 'sleep' : pet.mode === 'walk' && !hovering ? 'walk' : 'stand';
  drawPet(ctx, pet.x, groundY(), {
    animal: view.animal,
    stage: view.evolutionStage,
    colorPrimary: view.colorPrimary,
    colorSecondary: view.colorSecondary,
    phase: pet.phase,
    facing: pet.facing,
    pose,
  });

  const box = petBox();
  if (view.sleeping) drawText('Zz', box.right, box.top + 10, 14, 'rgba(60,60,90,0.8)');

  for (let i = hearts.length - 1; i >= 0; i--) {
    const h = hearts[i]!;
    const age = (now - h.born) / 1000;
    if (age > 1.2) {
      hearts.splice(i, 1);
      continue;
    }
    ctx.globalAlpha = 1 - age / 1.2;
    drawText('♥', h.x, h.y - age * 30, 16, '#e5484d');
    ctx.globalAlpha = 1;
  }

  if (bubble && now < bubble.until) drawBubble(bubble.text, pet.x, box.top - 4);
  else if (hovering) {
    drawBubble(`${view.nickname} Lv.${view.level}`, pet.x, box.top - 4);
    drawExpBar(pet.x, box.top + 2, view.levelProgress);
  }
}

function drawText(text: string, x: number, y: number, size: number, color: string): void {
  ctx.font = `bold ${size}px system-ui, sans-serif`;
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.fillText(text, x, y);
}

function drawBubble(text: string, x: number, bottom: number): void {
  ctx.font = '12px system-ui, sans-serif';
  const w = ctx.measureText(text).width + 14;
  const h = 20;
  const left = Math.min(Math.max(x - w / 2, 4), window.innerWidth - w - 4);
  const top = bottom - h - 6;
  ctx.fillStyle = 'rgba(255,255,255,0.95)';
  ctx.strokeStyle = 'rgba(0,0,0,0.25)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(left, top, w, h, 8);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = '#222';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, left + 7, top + h / 2 + 1);
  ctx.textBaseline = 'alphabetic';
}

function drawExpBar(x: number, y: number, progress: number): void {
  const w = 44;
  ctx.fillStyle = 'rgba(0,0,0,0.2)';
  ctx.fillRect(x - w / 2, y, w, 4);
  ctx.fillStyle = '#30a46c';
  ctx.fillRect(x - w / 2, y, w * progress, 4);
}

function say(text: string, ms = 2000): void {
  bubble = { text, until: performance.now() + ms };
}

// ---------- 마우스: 캐릭터 위에서만 클릭을 받는다 ----------

function setInteractive(next: boolean): void {
  if (next === interactive) return;
  interactive = next;
  bridge.setInteractive(next);
}

window.addEventListener('mousemove', (e) => {
  const b = petBox();
  hovering = e.clientX >= b.left && e.clientX <= b.right && e.clientY >= b.top && e.clientY <= b.bottom;
  setInteractive(hovering);
});

document.addEventListener('mouseleave', () => {
  hovering = false;
  setInteractive(false);
});

window.addEventListener('click', () => {
  if (!hovering) return;
  pet.jumpUntil = performance.now() + 350;
  say(view?.sleeping ? '쿨쿨…' : ['안녕!', '헤헤', '오늘도 화이팅!'][Math.floor(Math.random() * 3)]!, 1500);
});

window.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  if (hovering) bridge.openMenu();
});

// ---------- 메인 프로세스 이벤트 ----------

bridge.onView((v) => (view = v));

bridge.onEvent((event: PetEvent) => {
  const now = performance.now();
  switch (event.type) {
    case 'interacted':
      pet.jumpUntil = now + 400;
      say(event.kind === 'feed' ? '냠냠!' : '신난다!');
      for (let i = 0; i < 3; i++) hearts.push({ x: pet.x + (i - 1) * 12, y: petBox().top, born: now + i * 120 });
      break;
    case 'limit':
      say(event.kind === 'feed' ? '오늘은 배불러요' : '오늘은 많이 놀았어요');
      break;
    case 'levelUp':
      say(`레벨 업! Lv.${event.level}`, 3000);
      break;
    case 'evolved':
      say('진화했어요!', 4000);
      break;
  }
});

bridge.petReady();

// ---------- 루프 ----------

let last = performance.now();
function frame(now: number): void {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  update(dt, now);
  render(now);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
