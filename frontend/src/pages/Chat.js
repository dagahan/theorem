import { createElement } from "../core/utils.js";

export default function Chat() {
  const el = createElement("div", "chat-container");
  
  el.innerHTML = `
    <div class="chat-layout">
      <main class="chat-main">
        <div class="chat-header">
          <div class="chat-title">
            <h1>Theorem</h1>
            <p>AI-наставник для подготовки к ЕГЭ по математике</p>
          </div>
          <div class="chat-actions">
            <a href="#/" class="home-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9,22 9,12 15,12 15,22"/>
              </svg>
              Главная
            </a>
            <button class="theme-toggle">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="5"/>
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
              </svg>
            </button>
          </div>
        </div>
        
        <div class="chat-messages" id="chatMessages">
          <div class="message assistant">
            <div class="message-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 12l2 2 4-4"/>
                <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.5 0 2.91.37 4.15 1.02"/>
              </svg>
            </div>
            <div class="message-content">
              <div class="message-text">
                Привет! Я Theorem — ваш персональный наставник по математике для подготовки к ЕГЭ. 
                Я помогу вам:<br><br>
                📝 <strong>Генерировать задачи</strong> по темам ЕГЭ<br>
                ✅ <strong>Проверять ваши решения</strong> с подробным анализом<br>
                📚 <strong>Объяснять теорию</strong> простым языком<br>
                📊 <strong>Отслеживать прогресс</strong> и давать рекомендации<br><br>
                Какую тему хотите изучить или какую задачу решить?
              </div>
              <div class="message-time">Только что</div>
            </div>
          </div>
        </div>
        
        <div class="chat-input-container">
          <div class="quick-actions">
            <button class="quick-action-btn" data-action="generate-task">📝 Сгенерировать задачу</button>
            <button class="quick-action-btn" data-action="check-solution">✅ Проверить решение</button>
            <button class="quick-action-btn" data-action="explain-topic">📚 Объяснить тему</button>
          </div>
          <div class="chat-input-wrapper">
            <textarea 
              id="messageInput" 
              class="chat-input" 
              placeholder="Задайте вопрос по математике или попросите сгенерировать задачу..."
              rows="1"
            ></textarea>
            <button id="sendButton" class="send-button" disabled>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
              </svg>
            </button>
          </div>
          <div class="input-footer">
            <div class="footer-content">
              <p>Theorem может допускать ошибки. Проверяйте важную информацию.</p>
              <div class="keyboard-shortcuts">
                <span class="shortcut">Ctrl+Enter</span> отправить
                <span class="shortcut">Esc</span> очистить
                <span class="shortcut">Ctrl+K</span> фокус
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  `;
  
  setupChatInteractions(el);
  
  return el;
}

function setupChatInteractions(container) {
  const messageInput = container.querySelector('#messageInput');
  const sendButton = container.querySelector('#sendButton');
  const chatMessages = container.querySelector('#chatMessages');
  const themeToggle = container.querySelector('.theme-toggle');
  
  messageInput.addEventListener('input', () => {
    const hasText = messageInput.value.trim().length > 0;
    sendButton.disabled = !hasText;
    
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
  });
  
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendButton.disabled) {
        sendMessage();
      }
    }
  });
  
  sendButton.addEventListener('click', sendMessage);
  
  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  });
  
  // Добавляем анимацию появления сообщений
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1 && node.classList.contains('message')) {
          node.style.opacity = '0';
          node.style.transform = 'translateY(20px)';
          setTimeout(() => {
            node.style.transition = 'all 0.4s ease-out';
            node.style.opacity = '1';
            node.style.transform = 'translateY(0)';
          }, 50);
        }
      });
    });
  });
  
  observer.observe(chatMessages, { childList: true });
  
  // Добавляем горячие клавиши
  document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter для отправки
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!sendButton.disabled) {
        sendMessage();
      }
    }
    
    // Escape для очистки поля ввода
    if (e.key === 'Escape') {
      messageInput.value = '';
      messageInput.style.height = 'auto';
      sendButton.disabled = true;
      messageInput.blur();
    }
    
    // Ctrl/Cmd + K для фокуса на поле ввода
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      messageInput.focus();
    }
  });
  
  // Добавляем эффект частиц при отправке сообщения
  function createParticleEffect(x, y) {
    for (let i = 0; i < 8; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      particle.style.left = x + 'px';
      particle.style.top = y + 'px';
      particle.style.animationDelay = (i * 0.05) + 's';
      
      // Случайные направления для частиц
      const angle = (Math.PI * 2 * i) / 8;
      const distance = 30 + Math.random() * 20;
      const randomX = Math.cos(angle) * distance;
      const randomY = Math.sin(angle) * distance;
      
      particle.style.setProperty('--random-x', randomX + 'px');
      particle.style.setProperty('--random-y', randomY + 'px');
      
      document.body.appendChild(particle);
      
      setTimeout(() => particle.remove(), 1000);
    }
  }
  
  // Добавляем обработчик для эффекта частиц при отправке
  sendButton.addEventListener('click', (e) => {
    const rect = sendButton.getBoundingClientRect();
    createParticleEffect(rect.left + rect.width / 2, rect.top + rect.height / 2);
  });
  
  const quickActionBtns = container.querySelectorAll('.quick-action-btn');
  quickActionBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      // Эффект волны при клике
      createRippleEffect(e, btn);
      
      const action = btn.dataset.action;
      let message = '';
      
      switch(action) {
        case 'generate-task':
          message = 'Сгенерируйте задачу по алгебре для подготовки к ЕГЭ';
          break;
        case 'check-solution':
          message = 'Проверьте моё решение задачи';
          break;
        case 'explain-topic':
          message = 'Объясните тему по математике';
          break;
      }
      
      // Просто добавляем текст в поле ввода
      messageInput.value = message;
      messageInput.style.height = 'auto';
      sendButton.disabled = false;
      
      // Анимация фокуса на поле ввода
      messageInput.style.transform = 'scale(1.02)';
      setTimeout(() => {
        messageInput.style.transform = 'scale(1)';
      }, 200);
      
      // Фокусируемся на поле ввода
      messageInput.focus();
    });
  });
  
  // Функция для создания эффекта волны
  function createRippleEffect(event, element) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    ripple.classList.add('ripple');
    
    element.appendChild(ripple);
    
    setTimeout(() => ripple.remove(), 600);
  }
  
  function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    addMessage('user', message);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendButton.disabled = true;
    
    // Добавляем индикатор печати
    showTypingIndicator();
    
    setTimeout(() => {
      hideTypingIndicator();
      const responses = [
        'Отлично! Я помогу вам с этой задачей. Это демо-интерфейс — реальная интеграция с AI будет реализована, когда backend API будет готов.',
        'Понял ваш запрос! Как наставник по математике, я готов помочь с подготовкой к ЕГЭ. Пока что это демо-версия интерфейса.',
        'Хорошо! Я проанализирую вашу задачу и дам подробное объяснение. В полной версии будет интеграция с AI-моделью для генерации задач и проверки решений.'
      ];
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      addMessage('assistant', randomResponse);
    }, 2000 + Math.random() * 1000); // Случайная задержка для реалистичности
  }
  
  function showTypingIndicator() {
    const typingEl = document.createElement('div');
    typingEl.className = 'message assistant typing-indicator';
    typingEl.id = 'typingIndicator';
    
    typingEl.innerHTML = `
      <div class="message-avatar">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 12l2 2 4-4"/>
          <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.5 0 2.91.37 4.15 1.02"/>
        </svg>
      </div>
      <div class="message-content">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;
    
    chatMessages.appendChild(typingEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
  
  function hideTypingIndicator() {
    const typingEl = document.getElementById('typingIndicator');
    if (typingEl) {
      typingEl.style.opacity = '0';
      typingEl.style.transform = 'translateY(-10px)';
      setTimeout(() => typingEl.remove(), 300);
    }
  }
  
  function addMessage(role, text) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;
    
    const avatar = role === 'user' ? 
      `<div class="message-avatar user-avatar">У</div>` :
      `<div class="message-avatar">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 12l2 2 4-4"/>
          <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.5 0 2.91.37 4.15 1.02"/>
        </svg>
      </div>`;
    
    const messageActions = role === 'assistant' ? `
      <div class="message-actions">
        <button class="message-action-btn copy-btn" title="Копировать">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
        <button class="message-action-btn like-btn" title="Понравилось">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
          </svg>
        </button>
      </div>
    ` : '';
    
    messageEl.innerHTML = `
      ${avatar}
      <div class="message-content">
        <div class="message-text">${role === 'assistant' ? '' : text}</div>
        <div class="message-footer">
          <div class="message-time">${new Date().toLocaleTimeString('ru-RU')}</div>
          ${messageActions}
        </div>
      </div>
    `;
    
    chatMessages.appendChild(messageEl);
    
    // Для сообщений пользователя сразу показываем текст
    if (role === 'user') {
      // Плавная прокрутка с анимацией
      setTimeout(() => {
        chatMessages.scrollTo({
          top: chatMessages.scrollHeight,
          behavior: 'smooth'
        });
      }, 100);
    } else {
      // Для AI запускаем эффект печати
      typeMessage(messageEl.querySelector('.message-text'), text);
    }
    
    // Добавляем обработчики для кнопок действий
    if (role === 'assistant') {
      setupMessageActions(messageEl);
    }
  }
  
  // Функция для эффекта печати символов
  function typeMessage(element, text) {
    let index = 0;
    const cursor = document.createElement('span');
    cursor.className = 'typing-cursor';
    cursor.textContent = '|';
    element.appendChild(cursor);
    
    function typeNextChar() {
      if (index < text.length) {
        const char = text[index];
        element.insertBefore(document.createTextNode(char), cursor);
        index++;
        
        // Неравномерная скорость печати (ускорено в 2.5 раза)
        const baseDelay = 8; // базовая задержка (было 20)
        const randomDelay = Math.random() * 12; // случайная задержка (было 30)
        const punctuationDelay = /[.!?;:]/.test(char) ? 80 : 0; // пауза после знаков препинания (было 200)
        const spaceDelay = char === ' ' ? 20 : 0; // пауза после пробелов (было 50)
        
        const totalDelay = baseDelay + randomDelay + punctuationDelay + spaceDelay;
        
        setTimeout(typeNextChar, totalDelay);
        
        // Плавная прокрутка во время печати
        setTimeout(() => {
          chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
          });
        }, 50);
      } else {
        // Убираем курсор после завершения печати
        setTimeout(() => {
          cursor.remove();
        }, 500);
      }
    }
    
    // Небольшая задержка перед началом печати (ускорено в 2.5 раза)
    setTimeout(typeNextChar, 80);
  }
  
  function setupMessageActions(messageEl) {
    const copyBtn = messageEl.querySelector('.copy-btn');
    const likeBtn = messageEl.querySelector('.like-btn');
    
    copyBtn.addEventListener('click', () => {
      // Получаем текст без курсора печати
      const textElement = messageEl.querySelector('.message-text');
      const text = textElement.textContent.replace(/\|/g, '').trim();
      
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"/>
          </svg>
        `;
        copyBtn.style.color = 'var(--accent)';
        setTimeout(() => {
          copyBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          `;
          copyBtn.style.color = '';
        }, 2000);
      });
    });
    
    likeBtn.addEventListener('click', () => {
      likeBtn.style.color = 'var(--accent)';
      likeBtn.style.transform = 'scale(1.2)';
      setTimeout(() => {
        likeBtn.style.transform = 'scale(1)';
      }, 200);
    });
  }
}