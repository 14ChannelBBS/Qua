const board = window.location.href.split("/")[3];
const threadId = window.location.href.split("/")[4];

/*
  文字のコンテンツ側デコレーションに使用する関数
*/
function decoration(content) {
  return content.replace(/(https?:\/\/[^\s]+)/g, (url) => {
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
  レスのロードに使用する関数
*/
async function loadResponses() {
  const responsesElement = document.querySelector(".responses");

  const response = await fetch(`/api/boards/${board}/threads/${threadId}`);
  const responses = await response.json();

  responsesElement.textContent = "";
  for (let i = 0; i < responses.length; i++) {
    const response = responses[i];

    const element = document.createElement("div");
    element.classList.add("response");

    const responseDetailElement = document.createElement("span");
    responseDetailElement.classList.add("detail");
    responseDetailElement.innerHTML = `${
      i + 1
    } : <span style="color: green;"><b>${response.name}</b></span> : ${new Date(
      response.created_at
    ).toLocaleString()} ID: ${response.shown_id}`;
    element.append(responseDetailElement);

    const responseContentElement = document.createElement("p");
    responseContentElement.classList.add("content");
    responseContentElement.innerHTML = decoration(response.content);
    element.append(responseContentElement);

    responsesElement.append(element);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const loadingElement = document.querySelector(".is-loading");

  await loadResponses();

  loadingElement.style.display = "none";
});
