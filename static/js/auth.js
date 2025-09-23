async function showToken() {
  document.querySelector(".token").value = `#${getCookie("2ch_X")}`;
}

document.addEventListener("DOMContentLoaded", async () => {
  document.querySelector(".verification").addEventListener("click", () => {
    if (!getCookie("2ch_X")) {
      verificationPrompt(
        "0x4AAAAAAB2YKDxzOyD2mIbI",
        "以下のチェックボックスをクリックして認証を行ってください。認証を行った後、トークンが表示されますのでコピーしてください。",
        showToken
      );
    }
  });

  if (getCookie("2ch_X")) {
    await showToken();
  }
});
