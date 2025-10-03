import { createElement } from "../core/utils.js";

export default function Home() {
  const el = createElement("div", "home-container");
  
  el.innerHTML = `
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="gradient-text">Theorem</span>
        </h1>
        <p class="hero-subtitle">AI-наставник для подготовки к ЕГЭ</p>
        <p class="hero-description">
          Персональный помощник по математике, который генерирует задачи, 
          проверяет ваши решения и помогает подготовиться к ЕГЭ по профильной и базовой математике.
        </p>
        
        <div class="hero-actions">
          <a href="#/chat" class="btn btn-primary">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            Начать подготовку
          </a>
        </div>
      </div>
      
      <div class="hero-demo">
        <div class="demo-chat">
          <div class="demo-message user">
            <div class="demo-avatar">У</div>
            <div class="demo-content">Решите уравнение: 2x² - 7x + 3 = 0</div>
          </div>
          <div class="demo-message assistant">
            <div class="demo-avatar">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 12l2 2 4-4"/>
                <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.5 0 2.91.37 4.15 1.02"/>
              </svg>
            </div>
            <div class="demo-content">
              Отлично! Решаем квадратное уравнение:<br>
              <strong>Шаг 1:</strong> Найдём дискриминант<br>
              D = b² - 4ac = 49 - 24 = 25<br>
              <strong>Шаг 2:</strong> Найдём корни<br>
              x₁ = (7 + 5)/4 = 3<br>
              x₂ = (7 - 5)/4 = 0.5<br>
              <strong>Ответ:</strong> x = 3 или x = 0.5
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="features-section">
      <h2 class="section-title">Возможности наставника</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📝</div>
          <h3>Генерация задач</h3>
          <p>Получайте персональные задачи по темам ЕГЭ с разными уровнями сложности</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">✅</div>
          <h3>Проверка решений</h3>
          <p>Загружайте свои решения и получайте подробный анализ с объяснениями ошибок</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📚</div>
          <h3>Объяснение теории</h3>
          <p>Изучайте математические концепции с примерами и пошаговыми объяснениями</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>Отслеживание прогресса</h3>
          <p>Анализируйте свои успехи и получайте рекомендации по улучшению</p>
        </div>
      </div>
    </div>
    
    <div class="ege-info-section">
      <h2 class="section-title">Подготовка к ЕГЭ</h2>
      <div class="ege-types">
        <div class="ege-type-card">
          <h3>Базовая математика</h3>
          <ul>
            <li>Алгебра и начала анализа</li>
            <li>Геометрия</li>
            <li>Практические задачи</li>
            <li>21 задание</li>
          </ul>
        </div>
        <div class="ege-type-card">
          <h3>Профильная математика</h3>
          <ul>
            <li>Углублённая алгебра</li>
            <li>Тригонометрия</li>
            <li>Стереометрия</li>
            <li>32 задания</li>
          </ul>
        </div>
      </div>
    </div>
    
    <div class="cta-section">
      <div class="cta-content">
        <h2>Готовы к успешной сдаче ЕГЭ?</h2>
        <p>Начните подготовку с AI-наставником уже сегодня и получите высокий балл на экзамене.</p>
        <a href="#/chat" class="btn btn-primary btn-large">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Начать подготовку сейчас
        </a>
      </div>
    </div>
  `;
  
  setupHomeInteractions(el);
  
  return el;
}

function setupHomeInteractions(container) {
  // Добавляем плавную анимацию для кнопки
  const chatButton = container.querySelector('.btn-primary');
  chatButton.addEventListener('mouseenter', () => {
    chatButton.style.transform = 'translateY(-2px) scale(1.02)';
  });
  chatButton.addEventListener('mouseleave', () => {
    chatButton.style.transform = 'translateY(0) scale(1)';
  });
}
