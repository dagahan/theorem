import { createElement } from "../core/utils.js";
import { authManager } from "../auth.js";

export function Login() {
  const el = createElement("div", "auth-container");
  
  el.innerHTML = `
    <div class="auth-card">
      <div class="auth-header">
        <h1>Theorem</h1>
        <p>Войдите в свой аккаунт</p>
      </div>
      
      <form class="auth-form" id="loginForm">
        <div class="form-group">
          <label for="email">Email</label>
          <input 
            type="email" 
            id="email" 
            name="email" 
            required 
            placeholder="your@email.com"
            autocomplete="email"
          >
        </div>
        
        <div class="form-group">
          <label for="password">Пароль</label>
          <input 
            type="password" 
            id="password" 
            name="password" 
            required 
            placeholder="Введите пароль"
            autocomplete="current-password"
          >
        </div>
        
        <button type="submit" class="btn btn-primary btn-full" id="loginBtn">
          <span class="btn-text">Войти</span>
          <div class="btn-spinner" style="display: none;">
            <div class="spinner"></div>
          </div>
        </button>
        
        <div class="auth-error" id="loginError" style="display: none;"></div>
      </form>
      
      <div class="auth-footer">
        <p>Нет аккаунта? <a href="#/register" class="auth-link">Зарегистрироваться</a></p>
        <a href="#/" class="auth-link">← На главную</a>
      </div>
    </div>
  `;
  
  setupLoginForm(el);
  
  return el;
}

export function Register() {
  const el = createElement("div", "auth-container");
  
  el.innerHTML = `
    <div class="auth-card">
      <div class="auth-header">
        <h1>Theorem</h1>
        <p>Создайте новый аккаунт</p>
      </div>
      
      <form class="auth-form" id="registerForm">
        <div class="form-group">
          <label for="email">Email</label>
          <input 
            type="email" 
            id="email" 
            name="email" 
            required 
            placeholder="your@email.com"
            autocomplete="email"
          >
        </div>
        
        <div class="form-group">
          <label for="password">Пароль</label>
          <input 
            type="password" 
            id="password" 
            name="password" 
            required 
            minlength="8"
            placeholder="Минимум 8 символов"
            autocomplete="new-password"
          >
        </div>
        
        <div class="form-group">
          <label for="confirmPassword">Подтвердите пароль</label>
          <input 
            type="password" 
            id="confirmPassword" 
            name="confirmPassword" 
            required 
            placeholder="Повторите пароль"
            autocomplete="new-password"
          >
        </div>
        
        <button type="submit" class="btn btn-primary btn-full" id="registerBtn">
          <span class="btn-text">Зарегистрироваться</span>
          <div class="btn-spinner" style="display: none;">
            <div class="spinner"></div>
          </div>
        </button>
        
        <div class="auth-error" id="registerError" style="display: none;"></div>
      </form>
      
      <div class="auth-footer">
        <p>Уже есть аккаунт? <a href="#/login" class="auth-link">Войти</a></p>
        <a href="#/" class="auth-link">← На главную</a>
      </div>
    </div>
  `;
  
  setupRegisterForm(el);
  
  return el;
}

function setupLoginForm(container) {
  const form = container.querySelector('#loginForm');
  const loginBtn = container.querySelector('#loginBtn');
  const btnText = loginBtn.querySelector('.btn-text');
  const btnSpinner = loginBtn.querySelector('.btn-spinner');
  const errorEl = container.querySelector('#loginError');
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(form);
    const email = formData.get('email');
    const password = formData.get('password');
    
    setLoading(true);
    hideError();
    
    const result = await authManager.login(email, password);
    
    if (result.success) {
      location.hash = '#/chat';
    } else {
      showError(result.error);
    }
    
    setLoading(false);
  });
  
  function setLoading(loading) {
    loginBtn.disabled = loading;
    btnText.style.display = loading ? 'none' : 'block';
    btnSpinner.style.display = loading ? 'block' : 'none';
  }
  
  function showError(message) {
    errorEl.textContent = message;
    errorEl.style.display = 'block';
  }
  
  function hideError() {
    errorEl.style.display = 'none';
  }
}

function setupRegisterForm(container) {
  const form = container.querySelector('#registerForm');
  const registerBtn = container.querySelector('#registerBtn');
  const btnText = registerBtn.querySelector('.btn-text');
  const btnSpinner = registerBtn.querySelector('.btn-spinner');
  const errorEl = container.querySelector('#registerError');
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(form);
    const email = formData.get('email');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    
    if (password !== confirmPassword) {
      showError('Пароли не совпадают');
      return;
    }
    
    if (password.length < 8) {
      showError('Пароль должен содержать минимум 8 символов');
      return;
    }
    
    setLoading(true);
    hideError();
    
    const result = await authManager.register(email, password);
    
    if (result.success) {
      location.hash = '#/chat';
    } else {
      showError(result.error);
    }
    
    setLoading(false);
  });
  
  function setLoading(loading) {
    registerBtn.disabled = loading;
    btnText.style.display = loading ? 'none' : 'block';
    btnSpinner.style.display = loading ? 'block' : 'none';
  }
  
  function showError(message) {
    errorEl.textContent = message;
    errorEl.style.display = 'block';
  }
  
  function hideError() {
    errorEl.style.display = 'none';
  }
}