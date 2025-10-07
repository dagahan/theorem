
import { initTheme } from "./theme.js";
import { startRouter, route } from "./router.js";
import Home from "./pages/Home.js";
import Chat from "./pages/Chat.js";
import { Login, Register } from "./pages/Auth.js";
import { authManager } from "./auth.js";
import "./animations.js";
import "katex/dist/katex.min.css";

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
});

const app = document.getElementById("app");

route("/", () => {
  return Home();
});

route("/chat", () => {
  if (!authManager.isAuthenticated) {
    location.hash = "#/login";
    return;
  }
  return Chat();
});

route("/login", () => {
  if (authManager.isAuthenticated) {
    location.hash = "#/chat";
    return;
  }
  return Login();
});

route("/register", () => {
  if (authManager.isAuthenticated) {
    location.hash = "#/chat";
    return;
  }
  return Register();
});

startRouter(app);