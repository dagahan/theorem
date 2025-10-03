
import { initTheme } from "./theme.js";
import { startRouter, route } from "./router.js";
import Home from "./pages/Home.js";
import Chat from "./pages/Chat.js";
import "./animations.js";

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
});

const app = document.getElementById("app");

route("/", () => {
  return Home();
});

route("/chat", () => {
  return Chat();
});

startRouter(app);