const board = window.location.href.split("/")[3];

/*
  スレッドをスレッド一覧へ追加するために使用する関数
*/
function appendThread(threads, threadListElement) {
  threadListElement.textContent = "";
  for (let i = 0; i < threads.length; i++) {
    const thread = threads[i];

    const element = document.createElement("a");
    element.classList.add("box");
    element.href = `/${board}/${thread.id}`;
    element.title = `Owner ID: ${thread.ownerShownId}`;

    const threadTitleElement = document.createElement("p");
    threadTitleElement.innerHTML = `${emojiParse(thread.title)} (${
      thread.count
    })`;
    threadTitleElement.style.fontWeight = "bold";
    element.append(threadTitleElement);

    const dateTimeElement = document.createElement("p");
    dateTimeElement.textContent = `${new Date(
      thread.createdAt
    ).toLocaleString()}`;
    element.append(dateTimeElement);

    threadListElement.append(element);
  }
}

/*
  スレッド一覧のロードに使用する関数
*/
async function loadThreadList() {
  const threadListElement = document.querySelector(".thread-list");

  const response = await fetch(`/api/boards/${board}/threads`);
  const threads = await response.json();

  appendThread(threads, threadListElement);
}

/*
  スレッドを投稿する際に使用する関数
*/
async function post() {
  const title = document.querySelector(".form-title").value;
  const name = document.querySelector(".form-name").value;
  const command = document.querySelector(".form-command").value;
  const content = document.querySelector(".form-content").value;

  const response = await fetch(`/api/boards/${board}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ title, name, command, content }),
  });
  const jsonData = await response.json();

  if (response.status != 201) {
    switch (jsonData.detail) {
      case "VERIFICATION_REQUIRED":
        verificationPrompt(jsonData.sitekey, jsonData.message, post);
        break;
      default:
        let message = "";
        if (jsonData.message === undefined) {
          message = jsonData.detail;
        } else {
          message = jsonData.message;
        }

        alertMessage(message);
    }
    return;
  }

  alertMessage("投稿しました。3秒後にリダイレクトします。", "success");
  document.querySelector(".form-content").value = "";
  await new Promise((resolve) =>
    setTimeout(() => {
      window.location.href = `/${board}/${jsonData.id}`;
    }, 3000)
  );
}

document.addEventListener("DOMContentLoaded", async () => {
  const loadingElement = document.querySelector(".loadingPlzWait");
  const threadListElement = document.querySelector(".thread-list");

  await loadThreadList();

  const name = getCookie("NAME");
  if (name !== undefined)
    document.querySelector(".form-name").value = decodeURI(name);
  const mail = getCookie("MAIL");
  if (mail !== undefined)
    document.querySelector(".form-command").value = decodeURI(mail);

  const postButton = document.querySelector(".post");
  postButton.addEventListener("click", async () => {
    postButton.classList.add("is-loading");
    postButton.disabled = true;
    await post();
    postButton.classList.remove("is-loading");
    postButton.disabled = false;
  });

  connectGateway();
  sio.on("connect", () => {
    sio.emit("joinRoom", board);
  });

  sio.on("updateThreads", (threads) => {
    if (threads[0].board == board) {
      appendThread(jsonData.threads, threadListElement);
      playNotificationSound();
    }
  });

  loadingElement.style.display = "none";
});
