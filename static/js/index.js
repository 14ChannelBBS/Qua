async function loadBoards() {
  const response = await fetch("/api/boards");
  const boards = await response.json();

  const boardsElement = document.querySelector(".boards");
  boards.forEach((board) => {
    const boardButton = document.createElement("a");
    boardButton.className = "button is-primary is-fullwidth";
    boardButton.textContent = board.name;
    boardButton.href = board.id;

    boardsElement.append(boardButton);
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadBoards();
});
