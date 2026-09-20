const talk = document.querySelector('#talk');
const status = document.querySelector('#status');
const orbLabel = document.querySelector('#orb-label');
const sessionId = crypto.randomUUID();
let recognition;
let callActive = false;
let recognitionRunning = false;
let socket;

function setOrbState(state) {
  talk.classList.remove('active', 'user', 'agent');
  if (state) talk.classList.add('active', state);
  const labels = {
    idle: 'Начать разговор',
    user: 'Слушаю вас…',
    agent: 'Агент отвечает…',
  };
  orbLabel.textContent = labels[state] || labels.idle;
}

function speak(value) {
  if (recognition && recognitionRunning) recognition.stop();
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(value);
  utterance.lang = 'ru-RU';
  utterance.rate = 1;
  utterance.volume = 0.4;
  setOrbState('agent');
  utterance.onend = () => {
    setOrbState(callActive ? 'user' : 'idle');
    if (callActive && recognition && !recognitionRunning) {
      try { recognition.start(); } catch (_) {}
    }
  };
  speechSynthesis.speak(utterance);
}

async function sendMessage(value) {
  value = value.trim();
  if (!value) return;
  setOrbState('agent');
  status.textContent = 'Менеджер думает…';
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({session_id: sessionId, text: value}));
    return;
  }
  const response = await fetch('/api/v1/pub/agent/message', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({session_id: sessionId, text: value}),
  });
  if (!response.ok) {
    status.textContent = 'Ошибка соединения';
    setOrbState('idle');
    return;
  }
  handleAgentResponse(await response.json());
}

function handleAgentResponse(data) {
  speak(data.reply);
  status.textContent = data.order_id
    ? `Заказ создан: ${data.order_id}`
    : 'Готов слушать';
  if (data.order_id) loadOrders();
}

function connectAgentSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/pub/agent/ws`);
  socket.onopen = () => {
    status.textContent = 'Звонок подключён — говорите';
  };
  socket.onmessage = event => handleAgentResponse(JSON.parse(event.data));
  socket.onerror = () => {
    status.textContent = 'Ошибка WebSocket-соединения';
    setOrbState('idle');
  };
  socket.onclose = () => {
    if (callActive) status.textContent = 'Соединение закрыто';
  };
}

function setupRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    status.textContent = 'Голос недоступен в этом браузере';
    return null;
  }
  const r = new SpeechRecognition();
  r.lang = 'ru-RU';
  r.interimResults = false;
  r.continuous = true;
  r.onstart = () => {
    recognitionRunning = true;
    setOrbState('user');
    status.textContent = 'Слушаю вас…';
  };
  r.onend = () => {
    recognitionRunning = false;
    if (callActive && !speechSynthesis.speaking) {
      setOrbState('user');
      setTimeout(() => { try { recognition.start(); } catch (_) {} }, 250);
    } else if (!callActive) {
      setOrbState('idle');
    }
  };
  r.onerror = event => {
    if (event.error !== 'no-speech' && event.error !== 'aborted') {
      status.textContent = `Ошибка микрофона: ${event.error}`;
    }
  };
  r.onresult = event => sendMessage(event.results[0][0].transcript);
  return r;
}

function stopCall() {
  callActive = false;
  if (recognition) recognition.stop();
  speechSynthesis.cancel();
  if (socket) { socket.close(); socket = null; }
  setOrbState('idle');
  status.textContent = 'Разговор завершён';
}

recognition = setupRecognition();
talk.onclick = () => {
  if (!recognition) return;
  if (callActive) {
    stopCall();
    return;
  }
  callActive = true;
  connectAgentSocket();
  status.textContent = 'Подключаю звонок…';
  speak('Здравствуйте! Что хотите заказать?');
};

async function loadOrders() {
  const target = document.querySelector('#orders-list');
  const response = await fetch('/api/v1/pub/orders/');
  if (!response.ok) {
    target.innerHTML = '<p class="muted">Заказы пока недоступны.</p>';
    return;
  }
  const orders = await response.json();
  target.innerHTML = orders.length
    ? orders.map(order => `<article class="order"><div class="order-title"><span>${order.status}</span><span>${(order.total_price_minor / 100).toFixed(2)} ₽</span></div><small>Точка: ${order.branch} · ${order.delivery_type === 'delivery' ? 'Доставка' : 'Самовывоз'}</small><div>${order.items.map(item => `${item.title} × ${item.quantity}`).join(', ')}</div></article>`).join('')
    : '<p class="muted">Заказов пока нет.</p>';
}

document.querySelector('#refresh').onclick = loadOrders;
setOrbState('idle');
loadOrders();
