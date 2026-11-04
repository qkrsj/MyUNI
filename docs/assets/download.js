/* '최신 버전 받기' 를 이 컴퓨터에 맞는 파일로 바꾼다.

   릴리스 파일 이름은 버전 없이 고정이라(MyUNi-Setup.exe, MyUNi.dmg) 주소는 그대로 걸 수 있다:
     https://github.com/qkrsj/myuni/releases/latest/download/<이름>
   여기서는 (1) 운영체제에 맞는 파일을 고르고 (2) 깃허브에 최신 릴리스를 물어 버전을 적는다.
   아직 릴리스가 없으면 단추를 막고 알려준다. 물어보지 못하면 원래 주소가 그대로 남는다. */
(function () {
  var REPO = "qkrsj/myuni";
  var BASE = "https://github.com/" + REPO + "/releases/latest/download/";
  var FILES = { win: "MyUNi-Setup.exe", mac: "MyUNi.dmg" };
  var LABEL = { win: "Windows 용 받기", mac: "Mac 용 받기" };

  function device() {
    var ua = navigator.userAgent || "";
    var p = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
    if (/Android|iPhone|iPad|iPod/i.test(ua)) { return "mobile"; }
    if (/Win/i.test(p) || /Windows/i.test(ua)) { return "win"; }
    if (/Mac/i.test(p) || /Macintosh/i.test(ua)) { return "mac"; }
    return "other";
  }

  var auto = document.querySelector('a[data-download="auto"]');
  var label = auto && auto.querySelector("[data-label]");
  var notice = document.querySelector("[data-notice]");
  var mine = device();

  function say(text) {
    if (!notice) { return; }
    notice.textContent = text;
    notice.hidden = false;
  }

  if (auto && FILES[mine]) {
    auto.href = BASE + FILES[mine];
    if (label) { label.textContent = LABEL[mine]; }
  } else if (mine === "mobile") {
    say("MyUNi 는 Windows · Mac 컴퓨터용이에요. 컴퓨터에서 이 페이지를 열어 받아 주세요.");
  }

  if (!window.fetch) { return; }
  fetch("https://api.github.com/repos/" + REPO + "/releases/latest",
        { headers: { Accept: "application/vnd.github+json" } })
    .then(function (r) {
      if (r.status === 404) { throw new Error("none"); }
      if (!r.ok) { throw new Error("skip"); }
      return r.json();
    })
    .then(function (rel) {
      Array.prototype.forEach.call(document.querySelectorAll("[data-version]"), function (el) {
        el.textContent = " · 최신 " + rel.tag_name;
      });
    })
    .catch(function (e) {
      if (e && e.message === "none") {
        Array.prototype.forEach.call(document.querySelectorAll("a[data-download]"), function (a) {
          a.setAttribute("aria-disabled", "true");
          a.removeAttribute("href");
        });
        say("첫 버전을 준비하고 있어요. 조금만 기다려 주세요.");
      }
    });
})();
