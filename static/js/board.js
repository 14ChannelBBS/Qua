const board = window.location.href.split("/")[3];

/*
  スレッド一覧のロードに使用する関数
*/
async function loadThreadList() {
  const threadListElement = document.querySelector(".thread-list");

  const response = await fetch(`/api/boards/${board}/threads`);
  const threads = await response.json();

  threadListElement.textContent = "";
  for (let i = 0; i < threads.length; i++) {
    const thread = threads[i];

    const element = document.createElement("a");
    element.classList.add("box");
    element.href = `/${board}/${thread.id}`;
    element.title = `Owner ID: ${thread.owner_shown_id}`;

    const threadTitleElement = document.createElement("p");
    threadTitleElement.textContent = `${thread.title} (${thread.count})`;
    threadTitleElement.style.fontWeight = "bold";
    element.append(threadTitleElement);

    const dateTimeElement = document.createElement("p");
    dateTimeElement.textContent = `${new Date(
      thread.created_at
    ).toLocaleString()}`;
    element.append(dateTimeElement);

    threadListElement.append(element);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const loadingElement = document.querySelector(".is-loading");

  await loadThreadList();

  loadingElement.style.display = "none";
});
