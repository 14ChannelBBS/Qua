const board = window.location.href.split("/")[3];
const threadId = window.location.href.split("/")[4];
let threadCount = 0;

/*
  文字のコンテンツ側デコレーションに使用する関数
*/
function decoration(content) {
  return content
    .replace(/\n/g, "<br>")
    .replace(/(https?:\/\/[^\s]+)/g, (url) => {
      const youtubeRegex =
        /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)/;
      const spotifyRegex =
        /https?:\/\/open\.spotify\.com\/(?:[a-z-]+\/)?track\/([a-zA-Z0-9]+)/;
      const niconicoRegex =
        /(?:https?:\/\/)?(?:www\.)?(?:nicovideo\.jp\/watch\/|nico\.ms\/)([a-zA-Z0-9_-]+)/;

      const youtubeMatch = url.match(youtubeRegex);
      const spotifyMatch = url.match(spotifyRegex);
      const niconicoMatch = url.match(niconicoRegex);
      if (youtubeMatch) {
        const videoId = youtubeMatch[1];
        return `<iframe width="280" height="157" src="https://www.youtube.com/embed/${videoId}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen loading="lazy"></iframe>`;
      } else if (spotifyMatch) {
        const songId = spotifyMatch[1];
        return `<iframe data-testid="embed-iframe" style="border-radius:12px" src="https://open.spotify.com/embed/track/${songId}" width="100%" height="100" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>`;
      } else if (niconicoMatch) {
        const videoId = niconicoMatch[1];
        return `<script type="application/javascript" src="https://embed.nicovideo.jp/watch/${videoId}/script?w=320&h=180" loading="lazy"></script><noscript><a href="https://www.nicovideo.jp/watch/${videoId}">添付されたニコニコ動画の動画を再生</a></noscript>`;
      } else {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
      }
    });
}

/*
  レスの表示に使用する関数
*/
async function appendResponse(response, i, responsesElement) {
  const element = document.createElement("div");
  element.classList.add("response");

  const responseDetailElement = document.createElement("span");
  responseDetailElement.classList.add("detail");
  responseDetailElement.innerHTML = `${i + 1} : <span style="color: ${
    response.attributes.cap_color ?? "green"
  };"><b>${emojiParse(response.name)}@${
    response.attributes.cap ? emojiParse(response.attributes.cap) + " ★" : ""
  }</b></span> : ${new Date(response.created_at).toLocaleString()} ID: ${
    response.shown_id
  }`;
  element.append(responseDetailElement);

  const responseContentElement = document.createElement("p");
  responseContentElement.classList.add("content");
  responseContentElement.innerHTML = emojiParse(decoration(response.content));
  console.log(decoration(response.content));
  console.log(emojiParse(decoration(response.content)));
  element.append(responseContentElement);

  responsesElement.append(element);
}

/*
  レスのロードに使用する関数
*/
async function loadResponses() {
  const responsesElement = document.querySelector(".responses");

  const response = await fetch(`/api/boards/${board}/threads/${threadId}`);
  const responses = await response.json();

  responsesElement.textContent = "";
  for (let i = 0; i < responses.length; i++) {
    const response = responses[i];

    appendResponse(response, i, responsesElement);

    threadCount += 1;
  }
}

/*
  スレッドを投稿する際に使用する関数
*/
async function post() {
  const name = document.querySelector(".form-name").value;
  const command = document.querySelector(".form-command").value;
  const content = document.querySelector(".form-content").value;

  const response = await fetch(`/api/boards/${board}/threads/${threadId}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name, command, content }),
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

  alertMessage("投稿しました。", "success");
  document.querySelector(".form-content").value = "";
}

document.addEventListener("DOMContentLoaded", async () => {
  const loadingElement = document.querySelector(".loadingPlzWait");
  const responsesElement = document.querySelector(".responses");
  const threadInfoElement = document.querySelector(".thread-info");

  await loadResponses();

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
    sio.emit("joinRoom", `${board}_${threadId}`);
  });

  sio.on("newResponse", (response) => {
    const isAtBottom =
      threadInfoElement.scrollTop >= threadInfoElement.scrollHeight - 500;

    appendResponse(response, threadCount, responsesElement);
    threadCount += 1;

    if (isAtBottom) {
      threadInfoElement.scrollTop = threadInfoElement.scrollHeight;
    }

    playNotificationSound();
  });

  loadingElement.style.display = "none";
});
