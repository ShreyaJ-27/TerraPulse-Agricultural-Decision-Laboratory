import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  const apiUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
  return (
    <main className="shell">
      <p className="eyebrow">TerraPulse 2.0</p>
      <h1>A clear foundation for better farm decisions.</h1>
      <p className="intro">
        The farmer-facing experience will be built on shared scientific contracts and
        traceable data.
      </p>
      <div className="status" role="status">
        API base: <code>{apiUrl}</code>
      </div>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

