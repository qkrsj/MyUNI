const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const form = $<HTMLFormElement>('form');
const nickname = $<HTMLInputElement>('nickname');
const password = $<HTMLInputElement>('password');
const school = $<HTMLSelectElement>('school');
const submit = $<HTMLButtonElement>('submit');
const error = $<HTMLParagraphElement>('error');
const tabLogin = $<HTMLButtonElement>('tab-login');
const tabSignup = $<HTMLButtonElement>('tab-signup');

let mode: 'login' | 'signup' = 'login';
let schoolsLoaded = false;

function setMode(next: typeof mode): void {
  mode = next;
  tabLogin.setAttribute('aria-selected', String(mode === 'login'));
  tabSignup.setAttribute('aria-selected', String(mode === 'signup'));
  $('school-field').hidden = mode === 'login';
  $('notice').hidden = mode === 'login';
  submit.textContent = mode === 'login' ? '로그인' : '가입하고 시작하기';
  password.autocomplete = mode === 'login' ? 'current-password' : 'new-password';
  error.textContent = '';
  if (mode === 'signup' && !schoolsLoaded) void loadSchools();
}

async function loadSchools(): Promise<void> {
  try {
    const schools = await window.myuni.getSchools();
    for (const s of schools) school.add(new Option(s.name, String(s.id)));
    schoolsLoaded = true;
  } catch {
    error.textContent = '학교 목록을 불러오지 못했어요. 서버 연결을 확인해 주세요.';
  }
}

function validate(): string | null {
  const nick = nickname.value.trim();
  if (nick.length < 2 || nick.length > 16) return '닉네임은 2~16자로 입력해 주세요.';
  if (mode === 'signup' && !/^[0-9A-Za-z가-힣_]+$/.test(nick)) return '닉네임은 한글, 영문, 숫자, _ 만 쓸 수 있어요.';
  if (mode === 'signup' && password.value.length < 8) return '비밀번호는 8자 이상이어야 해요.';
  if (!password.value) return '비밀번호를 입력해 주세요.';
  return null;
}

tabLogin.addEventListener('click', () => setMode('login'));
tabSignup.addEventListener('click', () => setMode('signup'));

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const problem = validate();
  if (problem) {
    error.textContent = problem;
    return;
  }
  submit.disabled = true;
  error.textContent = '';
  const credentials = { nickname: nickname.value.trim(), password: password.value };
  const result =
    mode === 'login'
      ? await window.myuni.login(credentials)
      : await window.myuni.signup({ ...credentials, schoolId: school.value ? Number(school.value) : null });
  submit.disabled = false;
  if (!result.ok) error.textContent = result.message;
});

nickname.focus();
