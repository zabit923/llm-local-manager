const conversation = document.querySelector('#conversation');
const talk = document.querySelector('#talk');
const status = document.querySelector('#status');
const form = document.querySelector('#text-form');
const text = document.querySelector('#text');
const sessionId = crypto.randomUUID();
let recognition;
let callActive = false;
let recognitionRunning = false;
let socket;

function addBubble(kind, value) {
  const el = document.createElement('div');
  el.className = `bubble ${kind}`;
  el.textContent = value;
  conversation.appendChild(el);
  conversation.scrollTop = conversation.scrollHeight;
}

function speak(value) {
  if (recognition && recognitionRunning) recognition.stop();
  if ('speechSynthesis' in window) {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(value);
    utterance.lang = 'ru-RU';
    utterance.rate = 1;
    utterance.onend = () => {
      if (callActive && recognition && !recognitionRunning) {
        try { recognition.start(); } catch (_) {}
      }
    };
    speechSynthesis.speak(utterance);
  }
}

async function sendMessage(value) {
  value = value.trim();
  if (!value) return;
  addBubble('user', value);
  status.textContent = 'Менеджер думает…';
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({session_id: sessionId, text: value}));
    return;
  }
  const response = await fetch('/api/v1/pub/agent/message', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({session_id: sessionId, text: value}),
  });
  if (!response.ok) { addBubble('agent', 'Не удалось связаться с сервером.'); status.textContent = 'Ошибка'; return; }
  const data = await response.json();
  addBubble('agent', data.reply);
  speak(data.reply);
  status.textContent = data.order_id ? `Заказ создан: ${data.order_id}` : 'Готов слушать';
  if (data.order_id) loadOrders();
}

function connectAgentSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/pub/agent/ws`);
  socket.onopen = () => { status.textContent = 'Звонок подключён — говорите'; };
  socket.onmessage = event => {
    const data = JSON.parse(event.data);
    addBubble('agent', data.reply);
    speak(data.reply);
    status.textContent = data.order_id ? `Заказ создан: ${data.order_id}` : 'Готов слушать';
    if (data.order_id) loadOrders();
  };
  socket.onerror = () => { status.textContent = 'Ошибка WebSocket-соединения'; };
  socket.onclose = () => { if (callActive) status.textContent = 'Соединение закрыто'; };
}

function setupRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) { status.textContent = 'Голос недоступен — используйте текст'; return null; }
  const r = new SpeechRecognition();
  r.lang = 'ru-RU'; r.interimResults = false; r.continuous = true;
  r.onstart = () => { recognitionRunning = true; talk.classList.add('listening'); talk.textContent = 'Завершить звонок'; status.textContent = 'Звонок подключён — говорите'; };
  r.onend = () => {
    recognitionRunning = false;
    talk.classList.remove('listening');
    if (callActive) {
      status.textContent = 'Восстанавливаю соединение…';
      setTimeout(() => { try { recognition.start(); } catch (_) {} }, 250);
    } else {
      talk.textContent = 'Подключиться к звонку';
    }
  };
  r.onerror = event => {
    if (event.error !== 'no-speech' && event.error !== 'aborted') status.textContent = `Ошибка микрофона: ${event.error}`;
  };
  r.onresult = event => sendMessage(event.results[0][0].transcript);
  return r;
}

recognition = setupRecognition();
talk.onclick = () => {
  if (!recognition) { text.focus(); return; }
  if (callActive) {
    callActive = false;
    recognition.stop();
    speechSynthesis.cancel();
    if (socket) { socket.close(); socket = null; }
    status.textContent = 'Звонок завершён';
    talk.textContent = 'Подключиться к звонку';
  } else {
    callActive = true;
    connectAgentSocket();
    status.textContent = 'Подключаю звонок…';
    speak('Здравствуйте! Что хотите заказать?');
  }
};
form.onsubmit = event => { event.preventDefault(); const value = text.value; text.value = ''; sendMessage(value); };

async function loadOrders() {
  const target = document.querySelector('#orders-list');
  const response = await fetch('/api/v1/pub/orders/');
  if (!response.ok) { target.innerHTML = '<p class="muted">Заказы пока недоступны.</p>'; return; }
  const orders = await response.json();
  target.innerHTML = orders.length ? orders.map(order => `<article class="order"><div class="order-title"><span>${order.status}</span><span>${(order.total_price_minor / 100).toFixed(2)} ₽</span></div><small>Точка: ${order.branch} · ${order.delivery_type === 'delivery' ? 'Доставка' : 'Самовывоз'}</small><div>${order.items.map(item => `${item.title} × ${item.quantity}`).join(', ')}</div></article>`).join('') : '<p class="muted">Заказов пока нет.</p>';
}
document.querySelector('#refresh').onclick = loadOrders;
addBubble('agent', 'Здравствуйте! Что хотите заказать?');
loadOrders();
