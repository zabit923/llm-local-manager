const talk = document.querySelector('#talk');
const talkLabel = document.querySelector('#talk-label');
const status = document.querySelector('#status');
const orbLabel = document.querySelector('#orb-label');
const canvas = document.querySelector('#audio-visualizer');
const paint = canvas.getContext('2d');
let call = null;
let state = 'idle';
let animation;

function showState(value) {
  state = value;
  talk.classList.toggle('active', Boolean(call));
  talkLabel.textContent = call ? 'Завершить разговор' : 'Начать разговор';
  talk.setAttribute('aria-label', talkLabel.textContent);
  const labels = {
    connecting: 'Подключение…',
    listening: 'Слушаю вас',
    user: 'Слушаю вас',
    transcribing: 'Распознаю речь…',
    thinking: 'Менеджер думает…',
    speaking: 'Менеджер отвечает',
    idle: '',
  };
  orbLabel.textContent = labels[value] || '';
  status.textContent = orbLabel.textContent;
  drawAudio();
}

function showError(message) {
  orbLabel.className = 'button-label';
  orbLabel.textContent = message;
  status.textContent = message;
}

function drawAudio() {
  cancelAnimationFrame(animation);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const ratio = devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  paint.setTransform(ratio, 0, 0, ratio, 0, 0);
  paint.clearRect(0, 0, width, height);
  if (!call) return;
  const analyser = state === 'speaking'
    ? call.outputAnalyser
    : ['listening', 'user'].includes(state) ? call.micAnalyser : null;
  if (analyser) {
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    const bars = 40;
    const gap = 4;
    const barWidth = (width - gap * (bars - 1)) / bars;
    paint.fillStyle = '#ed2939';
    for (let i = 0; i < bars; i++) {
      const level = data[Math.floor(i * data.length / bars)] / 255;
      if (level < 0.04) continue;
      const size = Math.max(2, level * height);
      paint.fillRect(
        i * (barWidth + gap), (height - size) / 2, barWidth, size,
      );
    }
  }
  animation = requestAnimationFrame(drawAudio);
}

async function startCall() {
  const current = { capture: false, source: null };
  call = current;
  orbLabel.className = 'screen-reader-only';
  showState('connecting');
  try {
    current.context = new AudioContext();
    await current.context.resume();
    current.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    if (call !== current) {
      current.stream.getTracks().forEach(track => track.stop());
      return;
    }
    await current.context.audioWorklet.addModule(
      '/pcm-worklet.js?v=local-audio-1',
    );
    if (call !== current) return;
    current.micAnalyser = current.context.createAnalyser();
    current.outputAnalyser = current.context.createAnalyser();
    current.micAnalyser.fftSize = 256;
    current.outputAnalyser.fftSize = 256;
    current.captureNode = new AudioWorkletNode(
      current.context, 'pcm-capture',
    );
    const microphone = current.context.createMediaStreamSource(
      current.stream,
    );
    microphone.connect(current.micAnalyser);
    microphone.connect(current.captureNode);
    const mute = current.context.createGain();
    mute.gain.value = 0;
    current.captureNode.connect(mute).connect(current.context.destination);
    current.gain = current.context.createGain();
    current.gain.gain.value = 0.4;
    current.gain.connect(current.outputAnalyser);
    current.outputAnalyser.connect(current.context.destination);
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    current.socket = new WebSocket(
      protocol + '//' + location.host + '/api/v1/pub/agent/audio',
    );
    current.socket.binaryType = 'arraybuffer';
    current.captureNode.port.onmessage = event => {
      if (call === current && current.capture &&
          current.socket.readyState === WebSocket.OPEN &&
          current.socket.bufferedAmount < 65536) {
        current.socket.send(event.data);
      }
    };
    current.socket.onopen = () => {
      if (call !== current) return;
      current.socket.send(JSON.stringify({
        type: 'start', session_id: crypto.randomUUID(),
      }));
    };
    current.socket.onmessage = async event => {
      if (call !== current) return;
      try {
        if (typeof event.data === 'string') {
          const data = JSON.parse(event.data);
          if (data.type === 'state') {
            current.capture = ['listening', 'user'].includes(data.state);
            showState(data.state);
          } else if (data.type === 'reply' && data.order_id) {
            loadOrders();
          } else if (data.type === 'error') {
            stopCall();
            showError(data.message);
          }
          return;
        }
        current.capture = false;
        const buffer = await current.context.decodeAudioData(event.data);
        if (call !== current) return;
        const source = current.context.createBufferSource();
        current.source = source;
        source.buffer = buffer;
        source.connect(current.gain);
        source.onended = () => {
          if (call !== current) return;
          current.source = null;
          if (current.socket.readyState === WebSocket.OPEN) {
            current.socket.send(JSON.stringify({ type: 'playback_done' }));
          }
        };
        showState('speaking');
        source.start();
      } catch (error) {
        stopCall();
        showError('Не удалось воспроизвести ответ. Начните звонок заново.');
      }
    };
    current.socket.onclose = () => {
      if (call !== current) return;
      stopCall();
      showError('Звонок завершён. Нажмите кнопку, чтобы начать снова.');
    };
    current.socket.onerror = () => {
      if (call !== current) return;
      stopCall();
      showError('Голосовой сервис недоступен. Попробуйте позже.');
    };
  } catch (error) {
    if (call !== current) return;
    stopCall();
    showError(
      error.name === 'NotAllowedError'
        ? 'Разрешите доступ к микрофону в настройках браузера.'
        : 'Не удалось подключить микрофон. Откройте сайт через localhost.',
    );
  }
}

function stopCall() {
  const current = call;
  call = null;
  if (current) {
    current.capture = false;
    current.socket?.close();
    current.source?.stop();
    current.captureNode?.disconnect();
    current.stream?.getTracks().forEach(track => track.stop());
    current.context?.close();
  }
  showState('idle');
}

talk.onclick = () => call ? stopCall() : startCall();
window.addEventListener('pagehide', stopCall);

async function loadOrders() {
  const target = document.querySelector('#orders-list');
  try {
    const response = await fetch('/api/v1/pub/orders/');
    if (!response.ok) throw new Error('Orders unavailable');
    const orders = await response.json();
    target.replaceChildren();
    if (!orders.length) {
      target.textContent = 'Заказов пока нет.';
      return;
    }
    for (const order of orders) {
      const card = document.createElement('article');
      card.className = 'order';
      const header = document.createElement('div');
      header.className = 'order-title';
      header.textContent = 'Заказ · ' + new Intl.NumberFormat('ru-RU', {
        maximumFractionDigits: 2,
      }).format(order.total_price_minor / 100) + ' ₽';
      const branch = document.createElement('small');
      branch.textContent = 'Точка: ' + order.branch + ' · ' +
        (order.delivery_type === 'delivery' ? 'Доставка' : 'Самовывоз');
      const items = document.createElement('div');
      items.textContent = order.items
        .map(item => item.quantity + ' ' + item.title).join(', ');
      card.append(header, branch, items);
      target.append(card);
    }
  } catch (_) {
    target.textContent = 'Не удалось загрузить заказы.';
  }
}

document.querySelector('#refresh').onclick = loadOrders;
showState('idle');
loadOrders();
