"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  PauseCircle,
  PlayCircle,
  Power,
  RefreshCw,
  RotateCcw,
  Server,
  ShieldCheck,
  Square,
} from "lucide-react";

type BotState = {
  id: string;
  script: string;
  running: boolean;
  pid: number | null;
  exitCode: number | null;
  updatedAt: string;
};

type StatusPayload = {
  ok: boolean;
  bots: BotState[];
  runningCount: number;
  totalCount: number;
  serverTime: string;
  error?: string;
};

const botLabels: Record<string, string> = {
  bot: "Main Bot",
  drxfarm: "Farm Live",
  drxmusic: "Music",
  drxrolemanage: "Role Manager",
  drxsrvrmanage: "Server Manager",
  key_bot: "Key Bot",
  payment_bot: "Payment",
  script_panel: "Script Panel",
};

export default function Home() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState("");

  async function loadStatus() {
    setError("");
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      const payload = (await response.json()) as StatusPayload;
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Gagal mengambil status bot.");
      }
      setStatus(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mengambil status bot.");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(path: string, key: string) {
    setBusyKey(key);
    setError("");
    try {
      const response = await fetch(path, { method: "POST" });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Action gagal dijalankan.");
      }
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action gagal dijalankan.");
    } finally {
      setBusyKey("");
    }
  }

  useEffect(() => {
    loadStatus();
    const interval = window.setInterval(loadStatus, 5000);
    return () => window.clearInterval(interval);
  }, []);

  const runningPercent = useMemo(() => {
    if (!status?.totalCount) return 0;
    return Math.round((status.runningCount / status.totalCount) * 100);
  }, [status]);

  return (
    <main className="shell">
      <section className="topbar" aria-label="Ringkasan kontrol bot">
        <div>
          <p className="eyebrow">DRX Control</p>
          <h1>Bot Operations</h1>
        </div>
        <div className="top-actions">
          <button
            className="icon-button"
            type="button"
            onClick={loadStatus}
            disabled={loading || busyKey !== ""}
            title="Refresh status"
          >
            <RefreshCw size={18} />
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={() => runAction("/api/all/start", "all-start")}
            disabled={busyKey !== ""}
          >
            <PlayCircle size={18} />
            Start All
          </button>
          <button
            className="danger-button"
            type="button"
            onClick={() => runAction("/api/all/stop", "all-stop")}
            disabled={busyKey !== ""}
          >
            <Square size={18} />
            Stop All
          </button>
        </div>
      </section>

      <section className="summary-grid" aria-label="Status server">
        <div className="metric">
          <Activity size={20} />
          <div>
            <span>{status ? `${status.runningCount}/${status.totalCount}` : "-"}</span>
            <p>Bot aktif</p>
          </div>
        </div>
        <div className="metric">
          <Power size={20} />
          <div>
            <span>{runningPercent}%</span>
            <p>Kapasitas berjalan</p>
          </div>
        </div>
        <div className="metric">
          <Server size={20} />
          <div>
            <span>{status?.serverTime ? new Date(status.serverTime).toLocaleTimeString("id-ID") : "-"}</span>
            <p>Update terakhir</p>
          </div>
        </div>
        <div className="metric">
          <ShieldCheck size={20} />
          <div>
            <span>{error ? "Butuh cek" : "Terhubung"}</span>
            <p>Control API</p>
          </div>
        </div>
      </section>

      {error ? <div className="alert">{error}</div> : null}

      <section className="bot-grid" aria-label="Daftar bot">
        {loading && !status
          ? Array.from({ length: 6 }).map((_, index) => <div className="bot-card skeleton" key={index} />)
          : status?.bots.map((bot) => {
              const isBusy = busyKey.startsWith(bot.id) || busyKey.startsWith("all-");
              return (
                <article className="bot-card" key={bot.id}>
                  <div className="bot-head">
                    <div className="bot-icon">
                      <Bot size={22} />
                    </div>
                    <div>
                      <h2>{botLabels[bot.id] || bot.id}</h2>
                      <p>{bot.script}</p>
                    </div>
                    <span className={bot.running ? "status on" : "status off"}>
                      {bot.running ? "Active" : "Offline"}
                    </span>
                  </div>

                  <div className="bot-meta">
                    <span>PID</span>
                    <strong>{bot.pid ?? "-"}</strong>
                    <span>Exit</span>
                    <strong>{bot.exitCode ?? "-"}</strong>
                  </div>

                  <div className="bot-actions">
                    <button
                      className="primary-button compact"
                      type="button"
                      onClick={() => runAction(`/api/bots/${bot.id}/start`, `${bot.id}-start`)}
                      disabled={isBusy || bot.running}
                      title="Start bot"
                    >
                      <PlayCircle size={17} />
                      Start
                    </button>
                    <button
                      className="ghost-button compact"
                      type="button"
                      onClick={() => runAction(`/api/bots/${bot.id}/restart`, `${bot.id}-restart`)}
                      disabled={isBusy}
                      title="Restart bot"
                    >
                      <RotateCcw size={17} />
                      Restart
                    </button>
                    <button
                      className="danger-button compact"
                      type="button"
                      onClick={() => runAction(`/api/bots/${bot.id}/stop`, `${bot.id}-stop`)}
                      disabled={isBusy || !bot.running}
                      title="Stop bot"
                    >
                      <PauseCircle size={17} />
                      Stop
                    </button>
                  </div>
                </article>
              );
            })}
      </section>
    </main>
  );
}
