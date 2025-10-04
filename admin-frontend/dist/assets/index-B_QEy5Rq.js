(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const o of document.querySelectorAll('link[rel="modulepreload"]'))n(o);new MutationObserver(o=>{for(const a of o)if(a.type==="childList")for(const l of a.addedNodes)l.tagName==="LINK"&&l.rel==="modulepreload"&&n(l)}).observe(document,{childList:!0,subtree:!0});function s(o){const a={};return o.integrity&&(a.integrity=o.integrity),o.referrerPolicy&&(a.referrerPolicy=o.referrerPolicy),o.crossOrigin==="use-credentials"?a.credentials="include":o.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function n(o){if(o.ep)return;o.ep=!0;const a=s(o);fetch(o.href,a)}})();function k(t,e=""){const s=document.createElement(t);return e&&(s.className=e),s}function H(t){if(t===0)return"0 Bytes";const e=1024,s=["Bytes","KB","MB","GB"],n=Math.floor(Math.log(t)/Math.log(e));return parseFloat((t/Math.pow(e,n)).toFixed(2))+" "+s[n]}const d={ingestorApiBaseUrl:"http://localhost:50053",gatewayApiBaseUrl:"http://100.87.209.118:8080",qdrantApiBaseUrl:"http://localhost:6333",vllmMathApiBaseUrl:"http://localhost:50054",vllmTalkingApiBaseUrl:"http://192.168.2.187:50054",ingestorApiTimeout:3e4,adminFrontendHost:"192.168.0.102",adminFrontendPort:"4174",adminFrontendProtocol:"http",nodeEnv:"production",isDevelopment:!1,isProduction:!0};class U{constructor(e=d.ingestorApiBaseUrl){this.baseURL=e}async request(e,s={}){const n=`${this.baseURL}${e}`,o={headers:{"Content-Type":"application/json",...s.headers},...s},a=new AbortController,l=setTimeout(()=>a.abort(),d.ingestorApiTimeout);o.signal=a.signal;try{const i=await fetch(n,o);if(clearTimeout(l),!i.ok){const r=await i.json().catch(()=>({})),u=r.message||r.error||"Request failed";throw new h(i.status,u)}return await i.json()}catch(i){throw clearTimeout(l),i instanceof h?i:i.name==="TypeError"&&i.message.includes("fetch")?new h(0,"Ошибка сети. Проверьте подключение к серверу инжестора."):i.name==="AbortError"?new h(504,"Превышено время ожидания ответа."):new h(0,"Ошибка сети. Попробуйте еще раз.")}}async uploadRequest(e,s){const n=`${this.baseURL}${e}`,o=new AbortController,a=setTimeout(()=>o.abort(),d.ingestorApiTimeout);try{const l=await fetch(n,{method:"POST",body:s,signal:o.signal});if(clearTimeout(a),!l.ok){const i=await l.json().catch(()=>({})),r=i.message||i.error||"Upload failed";throw new h(l.status,r)}return await l.json()}catch(l){throw clearTimeout(a),l instanceof h?l:l.name==="TypeError"&&l.message.includes("fetch")?new h(0,"Ошибка сети. Проверьте подключение к серверу инжестора."):l.name==="AbortError"?new h(504,"Превышено время ожидания ответа."):new h(0,"Ошибка сети. Попробуйте еще раз.")}}async healthCheck(){return await this.request("/health")}async getServiceStats(){return await this.request("/statistics/service_stats")}async listCollections(){return await this.request("/vector-store/list_collections")}async getDocumentInfo(e,s=null){const n=new URLSearchParams;s&&n.append("collection_name",s);const o=n.toString(),a=`/vector-store/get_document_info/${e}${o?"?"+o:""}`;return await this.request(a)}async getDocumentEmbedded(e,s=null){const n=new URLSearchParams;s&&n.append("collection_name",s);const o=n.toString(),a=`/vector-store/get_document_embedded/${e}${o?"?"+o:""}`;return await this.request(a)}async getDocumentText(e,s=null){const n=new URLSearchParams;s&&n.append("collection_name",s);const o=n.toString(),a=`/vector-store/get_document_text/${e}${o?"?"+o:""}`;return await this.request(a)}async deleteDocuments(e,s=null){return await this.request("/ingestor/delete_documents",{method:"DELETE",body:JSON.stringify({doc_ids:e,collection_name:s})})}async ingestFiles(e,s,n={}){const o=new FormData;return e.forEach(a=>{o.append("files",a)}),o.append("collection_name",s),n&&Object.keys(n).length>0&&o.append("metadata",JSON.stringify(n)),await this.uploadRequest("/ingestor/ingest_files",o)}}let h=class extends Error{constructor(e,s){super(s),this.status=e,this.name="APIError"}};const p=new U;class P{constructor(){this.timeout=1e4}async request(e,s={}){const n={headers:{"Content-Type":"application/json",...s.headers},...s},o=new AbortController,a=setTimeout(()=>o.abort(),this.timeout);n.signal=o.signal;try{const l=await fetch(e,n);if(clearTimeout(a),!l.ok){const i=await l.json().catch(()=>({})),r=i.message||i.error||"Request failed";throw new m(l.status,r)}return await l.json()}catch(l){throw clearTimeout(a),l instanceof m?l:l.name==="TypeError"&&l.message.includes("fetch")?new m(0,"Ошибка сети. Проверьте подключение к сервису."):l.name==="AbortError"?new m(504,"Превышено время ожидания ответа."):new m(0,"Ошибка сети. Попробуйте еще раз.")}}async getGatewayHealth(){try{const e=await fetch(`${d.gatewayApiBaseUrl}/health`,{method:"GET",signal:AbortSignal.timeout(5e3)});return e.ok?await e.json():{status:"unknown",message:"Gateway доступен, но health endpoint не найден"}}catch{throw new m(0,"Gateway недоступен")}}async getGatewayStats(){return await this.request(`${d.gatewayApiBaseUrl}/stats`)}async getQdrantHealth(){var e,s;try{return{status:"healthy",collections:((s=(e=(await this.request(`${d.qdrantApiBaseUrl}/collections`)).result)==null?void 0:e.collections)==null?void 0:s.length)||0}}catch{throw new m(0,"Qdrant недоступен")}}async getQdrantCollections(){return await this.request(`${d.qdrantApiBaseUrl}/collections`)}async getQdrantCollectionInfo(e){return await this.request(`${d.qdrantApiBaseUrl}/collections/${e}`)}async getQdrantCollectionStats(e){return await this.request(`${d.qdrantApiBaseUrl}/collections/${e}/points/count`)}async getVllmMathHealth(){return await this.request(`${d.vllmMathApiBaseUrl}/health`)}async getVllmMathStats(){return await this.request(`${d.vllmMathApiBaseUrl}/stats`)}async getVllmTalkingHealth(){return await this.request(`${d.vllmTalkingApiBaseUrl}/health`)}async getVllmTalkingStats(){return await this.request(`${d.vllmTalkingApiBaseUrl}/stats`)}async getAllServicesHealth(){return(await Promise.allSettled([(async()=>{try{const s=await this.getGatewayHealth();return{name:"Gateway",status:"healthy",url:d.gatewayApiBaseUrl,data:s}}catch(s){return{name:"Gateway",status:"error",url:d.gatewayApiBaseUrl,error:s.message}}})(),(async()=>{try{const s=await this.getQdrantHealth();return{name:"Qdrant",status:"healthy",url:d.qdrantApiBaseUrl,data:s}}catch(s){return{name:"Qdrant",status:"error",url:d.qdrantApiBaseUrl,error:s.message}}})()])).map(s=>s.value||s.reason)}async getSystemStats(){try{const[e,s,n,o]=await Promise.allSettled([this.getGatewayStats(),this.getQdrantCollections(),this.getVllmMathStats(),this.getVllmTalkingStats()]);return{gateway:e.status==="fulfilled"?e.value:null,qdrant:s.status==="fulfilled"?s.value:null,vllmMath:n.status==="fulfilled"?n.value:null,vllmTalking:o.status==="fulfilled"?o.value:null}}catch(e){throw new m(0,`Ошибка получения статистики системы: ${e.message}`)}}}class m extends Error{constructor(e,s){super(s),this.status=e,this.name="APIError"}}const _=new P;class y{static getUserFriendlyMessage(e){if(typeof e=="string"&&!y.isTechnicalError(e))return e;if(e&&typeof e=="object"){const s=e.status||e.code,n=e.message||e.error;return n&&!y.isTechnicalError(n)?n:y.getStatusMessage(s)}return"Произошла неожиданная ошибка. Попробуйте еще раз."}static isTechnicalError(e){return typeof e!="string"?!1:["gRPC","localhost","Connection refused","UNKNOWN","StatusCode","AioRpcError","failed to connect","ipv6","ipv4","grpc_status","grpc_message","debug_error_string","Internal Server Error","Bad Gateway","Service Unavailable"].some(n=>e.toLowerCase().includes(n.toLowerCase()))}static getStatusMessage(e){switch(e){case 0:return"Ошибка сети. Проверьте подключение к серверу инжестора.";case 400:return"Неверные данные. Проверьте введенную информацию.";case 401:return"Доступ запрещен. Проверьте права доступа.";case 403:return"Доступ запрещен. Проверьте права доступа.";case 404:return"Запрашиваемый ресурс не найден.";case 409:return"Конфликт данных. Попробуйте еще раз.";case 422:return"Данные не прошли валидацию. Проверьте введенную информацию.";case 429:return"Слишком много запросов. Подождите немного и попробуйте снова.";case 500:return"Сервис инжестора временно недоступен. Попробуйте позже.";case 502:return"Сервис инжестора временно недоступен. Попробуйте позже.";case 503:return"Сервис перегружен. Попробуйте через несколько минут.";case 504:return"Превышено время ожидания ответа. Попробуйте еще раз.";default:return"Произошла ошибка. Попробуйте еще раз."}}static logError(e,s=""){y.isTechnicalError(e.message||e)?console.error(`[${s}] Technical error:`,e):console.warn(`[${s}] User error:`,e)}}const C=y.getUserFriendlyMessage,f=y.logError;function q(){const t=k("div","admin-container");return t.innerHTML=`
    <div class="admin-header">
      <div class="admin-title">
        <h1>Theorem Admin</h1>
        <p>Управление RAG базой данных</p>
      </div>
      <div class="admin-actions">
        <button class="theme-toggle" id="themeToggle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="admin-main">
      <div class="dashboard-grid" id="dashboardGrid">
        <div class="dashboard-card">
          <h3>Ingestor</h3>
          <p>Сервис инжеста документов</p>
          <div class="status-indicator status-unknown" id="ingestorStatus">
            <div class="spinner"></div>
            Проверка...
          </div>
        </div>
        
        <div class="dashboard-card">
          <h3>Gateway</h3>
          <p>Основной шлюз API</p>
          <div class="status-indicator status-unknown" id="gatewayStatus">
            <div class="spinner"></div>
            Проверка...
          </div>
        </div>
        
        <div class="dashboard-card">
          <h3>Qdrant</h3>
          <p>Векторная база данных</p>
          <div class="status-indicator status-unknown" id="qdrantStatus">
            <div class="spinner"></div>
            Проверка...
          </div>
        </div>
        
        
        <div class="dashboard-card">
          <h3>Коллекции</h3>
          <p>Количество векторных коллекций</p>
          <div class="dashboard-stat" id="collectionsCount">-</div>
        </div>
        
        <div class="dashboard-card">
          <h3>Векторы</h3>
          <p>Общее количество векторов</p>
          <div class="dashboard-stat" id="vectorsCount">-</div>
        </div>
        
        <div class="dashboard-card">
          <h3>Размерность</h3>
          <p>Размерность векторов</p>
          <div class="dashboard-stat-small" id="vectorDimensions">-</div>
        </div>
      </div>
      
      <div class="section">
        <div class="section-header">
          <h2>Быстрые действия</h2>
        </div>
        <div class="section-content">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
            <button class="btn btn-primary" id="refreshStatsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23,4 23,10 17,10"/>
                <polyline points="1,20 1,14 7,14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
              Обновить статистику
            </button>
            <button class="btn btn-secondary" id="manageCollectionsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18l-2 13H5L3 6z"/>
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
              Управление коллекциями
            </button>
            <button class="btn btn-success" id="uploadFilesBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7,10 12,15 17,10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Загрузить файлы
            </button>
            <button class="btn btn-warning" id="manageDocumentsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10,9 9,9 8,9"/>
              </svg>
              Управление документами
            </button>
          </div>
        </div>
      </div>
    </div>
  `,F(t),A(t),t}function F(t){const e=t.querySelector("#themeToggle"),s=t.querySelector("#refreshStatsBtn"),n=t.querySelector("#manageCollectionsBtn"),o=t.querySelector("#uploadFilesBtn"),a=t.querySelector("#manageDocumentsBtn");e.addEventListener("click",()=>{const i=document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark";document.documentElement.setAttribute("data-theme",i),localStorage.setItem("admin-theme",i)}),s.addEventListener("click",()=>{A(t)}),n.addEventListener("click",()=>{window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"collections"}}))}),o.addEventListener("click",()=>{window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"upload"}}))}),a.addEventListener("click",()=>{window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"documents"}}))})}async function A(t){const e=t.querySelector("#ingestorStatus"),s=t.querySelector("#gatewayStatus"),n=t.querySelector("#qdrantStatus"),o=t.querySelector("#collectionsCount"),a=t.querySelector("#vectorsCount"),l=t.querySelector("#vectorDimensions");try{const[i,r,u]=await Promise.allSettled([_.getAllServicesHealth(),p.getServiceStats(),p.listCollections()]);if(i.status==="fulfilled"&&i.value.forEach(v=>{const g=t.querySelector(`#${v.name.toLowerCase().replace(/\s+/g,"")}Status`);g&&(g.className=`status-indicator status-${O(v.status)}`,g.innerHTML=`${R(v.status)} ${v.status==="healthy"?"Работает":"Ошибка"}`)}),r.status==="fulfilled"){const c=r.value;a.textContent=c.total_vectors||0,l.textContent=c.hybrid_embedder_dim||0}if(u.status==="fulfilled"){const c=u.value;o.textContent=c.total_collections||0}try{await p.healthCheck(),e.className="status-indicator status-healthy",e.innerHTML="✓ Работает"}catch{e.className="status-indicator status-error",e.innerHTML="✗ Ошибка"}}catch(i){f(i,"Dashboard.loadDashboardData"),[e,s,n].forEach(r=>{r&&(r.className="status-indicator status-error",r.innerHTML="✗ Ошибка")}),o.textContent="-",a.textContent="-",l.textContent="-"}}function O(t){switch(t==null?void 0:t.toLowerCase()){case"healthy":case"ok":case"active":return"healthy";case"warning":case"degraded":return"warning";case"error":case"failed":case"down":return"error";default:return"unknown"}}function R(t){switch(t==null?void 0:t.toLowerCase()){case"healthy":case"ok":case"active":return"✓";case"warning":case"degraded":return"⚠";case"error":case"failed":case"down":return"✗";default:return"?"}}function V(){const t=k("div","admin-container");return t.innerHTML=`
    <div class="admin-header">
      <div class="admin-title">
        <h1>Управление коллекциями</h1>
        <p>Просмотр и управление векторными коллекциями</p>
      </div>
      <div class="admin-actions">
        <button class="btn btn-secondary" id="backBtn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          Назад
        </button>
        <button class="theme-toggle" id="themeToggle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="admin-main">
      <div class="section">
        <div class="section-header">
          <h2>Коллекции</h2>
        </div>
        <div class="section-content">
          <div class="loading" id="loadingIndicator">
            <div class="spinner"></div>
            Загрузка коллекций...
          </div>
          
          <div id="collectionsContent" style="display: none;">
            <div class="table-container">
              <table class="table" id="collectionsTable">
                <thead>
                  <tr>
                    <th>Название</th>
                    <th>Статус</th>
                    <th>Документы</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody id="collectionsTableBody">
                </tbody>
              </table>
            </div>
          </div>
          
          <div class="empty-state" id="emptyState" style="display: none;">
            <h3>Коллекции не найдены</h3>
            <p>В системе пока нет векторных коллекций</p>
            <button class="btn btn-primary" id="refreshCollectionsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23,4 23,10 17,10"/>
                <polyline points="1,20 1,14 7,14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
              Обновить
            </button>
          </div>
        </div>
      </div>
    </div>
  `,G(t),x(t),t}function G(t){const e=t.querySelector("#backBtn"),s=t.querySelector("#themeToggle"),n=t.querySelector("#refreshCollectionsBtn");e.addEventListener("click",()=>{window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"dashboard"}}))}),s.addEventListener("click",()=>{const a=document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark";document.documentElement.setAttribute("data-theme",a),localStorage.setItem("admin-theme",a)}),n.addEventListener("click",()=>{x(t)})}async function x(t){const e=t.querySelector("#loadingIndicator"),s=t.querySelector("#collectionsContent"),n=t.querySelector("#emptyState"),o=t.querySelector("#collectionsTableBody");e.style.display="flex",s.style.display="none",n.style.display="none";try{const a=await p.listCollections();e.style.display="none",a.collections&&a.collections.length>0?(s.style.display="block",j(o,a.collections)):n.style.display="block"}catch(a){f(a,"Collections.loadCollections"),e.style.display="none",n.style.display="block";const l=C(a);n.innerHTML=`
      <h3>Ошибка загрузки</h3>
      <p>${l}</p>
      <button class="btn btn-primary" id="refreshCollectionsBtn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23,4 23,10 17,10"/>
          <polyline points="1,20 1,14 7,14"/>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
        </svg>
        Попробовать снова
      </button>
    `,n.querySelector("#refreshCollectionsBtn").addEventListener("click",()=>{x(t)})}}function j(t,e){t.innerHTML="",e.forEach(s=>{const n=document.createElement("tr"),o=N(s.status),a=z(s.status);n.innerHTML=`
      <td>
        <div style="font-weight: 500;">${s.name}</div>
      </td>
      <td>
        <div class="status-indicator status-${o}">
          ${a} ${s.status}
        </div>
      </td>
      <td>
        <div>${s.documents?s.documents.length:0} документов</div>
      </td>
      <td>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-small btn-secondary" onclick="viewCollectionDetails('${s.name}')">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            Подробнее
          </button>
        </div>
      </td>
    `,t.appendChild(n)})}function N(t){switch(t==null?void 0:t.toLowerCase()){case"healthy":case"ok":case"active":return"healthy";case"warning":case"degraded":return"warning";case"error":case"failed":case"down":return"error";default:return"unknown"}}function z(t){switch(t==null?void 0:t.toLowerCase()){case"healthy":case"ok":case"active":return"✓";case"warning":case"degraded":return"⚠";case"error":case"failed":case"down":return"✗";default:return"?"}}window.viewCollectionDetails=function(t){window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"documents",collection:t}}))};function Q(t=null){const e=k("div","admin-container");return e.innerHTML=`
    <div class="admin-header">
      <div class="admin-title">
        <h1>Управление документами</h1>
        <p>${t?`Коллекция: ${t}`:"Просмотр и управление документами"}</p>
      </div>
      <div class="admin-actions">
        <button class="btn btn-secondary" id="backBtn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          Назад
        </button>
        <button class="theme-toggle" id="themeToggle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="admin-main">
      <div class="section">
        <div class="section-header">
          <h2>Документы</h2>
        </div>
        <div class="section-content">
          <div class="loading" id="loadingIndicator">
            <div class="spinner"></div>
            Загрузка документов...
          </div>
          
          <div id="documentsContent" style="display: none;">
            <div class="table-container">
              <table class="table" id="documentsTable">
                <thead>
                  <tr>
                    <th>
                      <input type="checkbox" id="selectAllCheckbox">
                    </th>
                    <th>ID документа</th>
                    <th>Чанки</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody id="documentsTableBody">
                </tbody>
              </table>
            </div>
            
            <div style="margin-top: 16px; display: flex; gap: 12px; align-items: center;">
              <button class="btn btn-error" id="deleteSelectedBtn" disabled>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3,6 5,6 21,6"/>
                  <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"/>
                </svg>
                Удалить выбранные
              </button>
              <span id="selectedCount" style="color: var(--muted); font-size: 14px;">0 выбрано</span>
            </div>
          </div>
          
          <div class="empty-state" id="emptyState" style="display: none;">
            <h3>Документы не найдены</h3>
            <p>В коллекции пока нет документов</p>
            <button class="btn btn-primary" id="refreshDocumentsBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23,4 23,10 17,10"/>
                <polyline points="1,20 1,14 7,14"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
              Обновить
            </button>
          </div>
        </div>
      </div>
    </div>
  `,J(e,t),S(e,t),e}function J(t,e){const s=t.querySelector("#backBtn"),n=t.querySelector("#themeToggle"),o=t.querySelector("#refreshDocumentsBtn"),a=t.querySelector("#selectAllCheckbox"),l=t.querySelector("#deleteSelectedBtn");t.querySelector("#selectedCount"),s.addEventListener("click",()=>{window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"collections"}}))}),n.addEventListener("click",()=>{const r=document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark";document.documentElement.setAttribute("data-theme",r),localStorage.setItem("admin-theme",r)}),o.addEventListener("click",()=>{S(t,e)}),a.addEventListener("change",()=>{t.querySelectorAll('input[type="checkbox"]:not(#selectAllCheckbox)').forEach(r=>{r.checked=a.checked}),B(t)}),l.addEventListener("click",()=>{const i=D(t);i.length>0&&$(i,e,t)}),t.addEventListener("change",i=>{i.target.type==="checkbox"&&i.target!==a&&B(t)})}function B(t){const e=D(t),s=t.querySelector("#selectedCount"),n=t.querySelector("#deleteSelectedBtn");s.textContent=`${e.length} выбрано`,n.disabled=e.length===0}function D(t){const e=t.querySelectorAll('input[type="checkbox"]:not(#selectAllCheckbox):checked');return Array.from(e).map(s=>s.dataset.docId)}async function S(t,e){const s=t.querySelector("#loadingIndicator"),n=t.querySelector("#documentsContent"),o=t.querySelector("#emptyState"),a=t.querySelector("#documentsTableBody");s.style.display="flex",n.style.display="none",o.style.display="none";try{const l=await p.listCollections();s.style.display="none";let i=[];if(e){const r=l.collections.find(u=>u.name===e);i=r?r.documents:[]}else i=l.collections.flatMap(r=>r.documents||[]);i.length>0?(n.style.display="block",await K(a,i,e)):o.style.display="block"}catch(l){f(l,"Documents.loadDocuments"),s.style.display="none",o.style.display="block";const i=C(l);o.innerHTML=`
      <h3>Ошибка загрузки</h3>
      <p>${i}</p>
      <button class="btn btn-primary" id="refreshDocumentsBtn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23,4 23,10 17,10"/>
          <polyline points="1,20 1,14 7,14"/>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
        </svg>
        Попробовать снова
      </button>
    `,o.querySelector("#refreshDocumentsBtn").addEventListener("click",()=>{S(t,e)})}}async function K(t,e,s){t.innerHTML="";for(const n of e){const o=document.createElement("tr");try{const a=await p.getDocumentInfo(n,s);o.innerHTML=`
        <td>
          <input type="checkbox" data-doc-id="${n}">
        </td>
        <td>
          <div style="font-weight: 500; font-family: monospace;">${n}</div>
        </td>
        <td>
          <div>${a.chunks_count||0} чанков</div>
        </td>
        <td>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-small btn-secondary" onclick="viewDocumentDetails('${n}', '${s||""}')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              Подробнее
            </button>
            <button class="btn btn-small btn-error" onclick="deleteDocument('${n}', '${s||""}')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3,6 5,6 21,6"/>
                <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"/>
              </svg>
              Удалить
            </button>
          </div>
        </td>
      `}catch{o.innerHTML=`
        <td>
          <input type="checkbox" data-doc-id="${n}">
        </td>
        <td>
          <div style="font-weight: 500; font-family: monospace;">${n}</div>
        </td>
        <td>
          <div style="color: var(--error);">Ошибка загрузки</div>
        </td>
        <td>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-small btn-error" onclick="deleteDocument('${n}', '${s||""}')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3,6 5,6 21,6"/>
                <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"/>
              </svg>
              Удалить
            </button>
          </div>
        </td>
      `}t.appendChild(o)}}function $(t,e,s){const n=X(t,e,s);document.body.appendChild(n)}function X(t,e,s){const n=document.createElement("div");n.className="modal active",n.innerHTML=`
    <div class="modal-content">
      <div class="modal-header">
        <h3>Подтверждение удаления</h3>
        <button class="modal-close" id="closeModal">×</button>
      </div>
      <div class="modal-body">
        <p>Вы уверены, что хотите удалить следующие документы?</p>
        <ul style="margin: 16px 0; padding-left: 20px;">
          ${t.map(c=>`<li style="font-family: monospace;">${c}</li>`).join("")}
        </ul>
        <p style="color: var(--error); font-weight: 500;">Это действие нельзя отменить!</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" id="cancelDelete">Отмена</button>
        <button class="btn btn-error" id="confirmDelete">
          <div class="loading" id="deleteLoading" style="display: none;">
            <div class="spinner"></div>
            Удаление...
          </div>
          <span id="deleteText">Удалить</span>
        </button>
      </div>
    </div>
  `;const o=n.querySelector("#closeModal"),a=n.querySelector("#cancelDelete"),l=n.querySelector("#confirmDelete"),i=n.querySelector("#deleteLoading"),r=n.querySelector("#deleteText"),u=()=>{document.body.removeChild(n)};return o.addEventListener("click",u),a.addEventListener("click",u),l.addEventListener("click",async()=>{i.style.display="flex",r.style.display="none",l.disabled=!0;try{await p.deleteDocuments(t,e),u(),S(s,e)}catch(c){f(c,"Documents.deleteDocuments"),alert(`Ошибка удаления: ${C(c)}`)}finally{i.style.display="none",r.style.display="inline",l.disabled=!1}}),n}window.viewDocumentDetails=function(t,e){window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"document-details",docId:t,collectionName:e}}))};window.deleteDocument=function(t,e){$([t],e,document.querySelector(".admin-container"))};function W(){const t=k("div","admin-container");return t.innerHTML=`
    <div class="admin-header">
      <div class="admin-title">
        <h1>Загрузка файлов</h1>
        <p>Загрузка документов в векторную базу данных</p>
      </div>
      <div class="admin-actions">
        <button class="btn btn-secondary" id="backBtn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          Назад
        </button>
        <button class="theme-toggle" id="themeToggle">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="admin-main">
      <div class="section">
        <div class="section-header">
          <h2>Загрузка файлов</h2>
        </div>
        <div class="section-content">
          <form id="uploadForm">
            <div class="form-group">
              <label for="collectionName">Коллекция</label>
              <select id="collectionName" required>
                <option value="">Выберите коллекцию</option>
                <option value="default">default</option>
              </select>
            </div>
            
            <div class="form-group">
              <label for="metadata">Метаданные (JSON)</label>
              <textarea id="metadata" placeholder='{"source": "admin", "version": "1.0"}'></textarea>
            </div>
            
            <div class="form-group">
              <label>Файлы для загрузки</label>
              <div class="file-upload" id="fileUpload">
                <input type="file" id="fileInput" multiple accept=".pdf,.txt,.docx,.md,.html">
                <div>
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom: 16px; color: var(--muted);">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7,10 12,15 17,10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  <p style="margin-bottom: 8px; font-weight: 500;">Перетащите файлы сюда или нажмите для выбора</p>
                  <p style="color: var(--muted); font-size: 14px;">Поддерживаемые форматы: PDF, TXT, DOCX, MD, HTML</p>
                </div>
              </div>
            </div>
            
            <div class="file-list" id="fileList" style="display: none;">
            </div>
            
            <div class="form-group">
              <button type="submit" class="btn btn-primary btn-large" id="uploadBtn">
                <div class="loading" id="uploadLoading" style="display: none;">
                  <div class="spinner"></div>
                  Загрузка...
                </div>
                <span id="uploadText">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7,10 12,15 17,10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  Загрузить файлы
                </span>
              </button>
            </div>
          </form>
          
          <div id="uploadResults" style="display: none;">
          </div>
        </div>
      </div>
    </div>
  `,Y(t),I(t),t}function Y(t){const e=t.querySelector("#backBtn"),s=t.querySelector("#themeToggle"),n=t.querySelector("#fileUpload"),o=t.querySelector("#fileInput");t.querySelector("#fileList");const a=t.querySelector("#uploadForm"),l=t.querySelector("#uploadBtn"),i=t.querySelector("#uploadLoading"),r=t.querySelector("#uploadText"),u=t.querySelector("#uploadResults");e.addEventListener("click",()=>{window.dispatchEvent(new CustomEvent("navigate",{detail:{page:"dashboard"}}))}),s.addEventListener("click",()=>{const v=document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark";document.documentElement.setAttribute("data-theme",v),localStorage.setItem("admin-theme",v)}),n.addEventListener("click",()=>{o.click()}),o.addEventListener("change",c=>{L(c.target.files,t)}),n.addEventListener("dragover",c=>{c.preventDefault(),n.classList.add("dragover")}),n.addEventListener("dragleave",()=>{n.classList.remove("dragover")}),n.addEventListener("drop",c=>{c.preventDefault(),n.classList.remove("dragover"),L(c.dataTransfer.files,t)}),a.addEventListener("submit",async c=>{c.preventDefault();const v=t.querySelector("#collectionName"),g=t.querySelector("#newCollectionName"),T=t.querySelector("#metadata").value,M=Array.from(o.files);let w=v.value;if(!w&&g.style.display==="block"&&(w=g.value.trim(),!w)){alert("Пожалуйста, введите название новой коллекции");return}if(!w){alert("Пожалуйста, выберите коллекцию или введите название новой");return}if(M.length===0){alert("Пожалуйста, выберите файлы для загрузки");return}let E={};if(T.trim())try{E=JSON.parse(T)}catch{alert("Неверный формат JSON в метаданных");return}i.style.display="flex",r.style.display="none",l.disabled=!0;try{const b=await p.ingestFiles(M,w,E);Z(b,u),I(t)}catch(b){f(b,"Upload.uploadFiles"),alert(`Ошибка загрузки: ${C(b)}`)}finally{i.style.display="none",r.style.display="flex",l.disabled=!1}})}function L(t,e){const s=e.querySelector("#fileList");if(t.length===0){s.style.display="none";return}s.style.display="block",s.innerHTML="",Array.from(t).forEach(n=>{const o=document.createElement("div");o.className="file-item",o.innerHTML=`
      <div class="file-info">
        <div class="file-name">${n.name}</div>
        <div class="file-size">${H(n.size)}</div>
      </div>
      <button class="file-remove" onclick="removeFile(this)">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    `,s.appendChild(o)})}function Z(t,e){e.style.display="block";const s=t.successful_files||0,n=t.failed_files||0;let a=`
    <div class="section">
      <div class="section-header">
        <h2>Результаты загрузки</h2>
      </div>
      <div class="section-content">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px;">
          <div class="dashboard-card">
            <h3>Всего файлов</h3>
            <div class="dashboard-stat">${t.total_files||0}</div>
          </div>
          <div class="dashboard-card">
            <h3>Успешно</h3>
            <div class="dashboard-stat" style="color: var(--success);">${s}</div>
          </div>
          <div class="dashboard-card">
            <h3>Ошибки</h3>
            <div class="dashboard-stat" style="color: var(--error);">${n}</div>
          </div>
        </div>
  `;t.items&&t.items.length>0&&(a+=`
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>Файл</th>
              <th>ID документа</th>
              <th>Статус</th>
              <th>Ошибка</th>
            </tr>
          </thead>
          <tbody>
    `,t.items.forEach(l=>{const i=l.status==="success"?"success":"error",r=l.status==="success"?"✓":"✗";a+=`
        <tr>
          <td>${l.filename}</td>
          <td style="font-family: monospace;">${l.doc_id}</td>
          <td>
            <div class="status-indicator status-${i}">
              ${r} ${l.status}
            </div>
          </td>
          <td>${l.error||"-"}</td>
        </tr>
      `}),a+=`
          </tbody>
        </table>
      </div>
    `),a+=`
      </div>
    </div>
  `,e.innerHTML=a}async function I(t){const e=t.querySelector("#collectionName");try{const s=await p.listCollections();e.innerHTML='<option value="">Выберите коллекцию</option>',s.collections&&s.collections.length>0&&s.collections.forEach(a=>{const l=document.createElement("option");l.value=a.name,l.textContent=`${a.name} (${a.documents?a.documents.length:0} документов)`,e.appendChild(l)});const n=document.createElement("option");n.value="",n.textContent="Создать новую коллекцию",n.disabled=!0,e.appendChild(n);const o=document.createElement("input");o.type="text",o.placeholder="Введите название новой коллекции",o.style.display="none",o.style.marginTop="8px",o.id="newCollectionName",e.parentElement.appendChild(o),e.addEventListener("change",a=>{a.target.value===""?(o.style.display="block",o.required=!0):(o.style.display="none",o.required=!1)})}catch(s){f(s,"Upload.loadCollections"),e.innerHTML='<option value="">Выберите коллекцию</option>';const n=document.createElement("option");n.value="default",n.textContent="default (будет создана)",e.appendChild(n)}}window.removeFile=function(t){const e=t.closest(".file-item"),s=e.parentElement;e.remove(),s.children.length===0&&(s.style.display="none")};class tt{constructor(){this.currentPage="dashboard",this.currentParams={},this.app=document.getElementById("app"),this.init()}init(){this.setupNavigation(),this.navigateTo("dashboard")}setupNavigation(){window.addEventListener("navigate",e=>{const{page:s,...n}=e.detail;this.navigateTo(s,n)})}navigateTo(e,s={}){this.currentPage=e,this.currentParams=s;let n;switch(e){case"dashboard":n=q();break;case"collections":n=V();break;case"documents":n=Q(s.collection);break;case"upload":n=W();break;default:n=q()}this.app.innerHTML="",this.app.appendChild(n)}}document.addEventListener("DOMContentLoaded",()=>{new tt});
