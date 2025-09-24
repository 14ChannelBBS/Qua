let sio = null;

function alertInit() {
  (document.querySelectorAll(".notification .delete") || []).forEach(
    ($delete) => {
      const $notification = $delete.parentNode;

      $delete.addEventListener("click", () => {
        $notification.parentNode.removeChild($notification);
      });
    }
  );
}

function alertMessage(message, status = "danger") {
  const notifications = document.querySelector(".notifications");

  const element = document.createElement("div");
  element.className = `notification is-${status}`;
  element.textContent = message;

  const button = document.createElement("button");
  button.className = "delete";
  element.append(button);

  notifications.append(element);
  alertInit();
}

function connectGateway() {
  sio = io();
}

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
}

const AudioContext =
  window.AudioContext ||
  window.webkitAudioContext ||
  window.mozAudioContext ||
  window.oAudioContext ||
  window.msAudioContext;
const audioContext = new AudioContext();

let source = audioContext.createBufferSource();
let audioBuffer;

fetch("/static/sounds/notification.mp3")
  .then((response) => response.arrayBuffer())
  .then((arrayBuffer) => audioContext.decodeAudioData(arrayBuffer))
  .then((buffer) => {
    audioBuffer = buffer;
  })
  .catch((error) => console.error(error));

function playNotificationSound() {
  if (!audioBuffer) return;

  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  source.start();
}
