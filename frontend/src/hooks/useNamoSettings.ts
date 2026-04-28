import { useState, useCallback } from "react";

const LS_KEY = "namo_server_settings";

export interface NamoSettings {
  mode: "local" | "tunnel";
  localIp: string;
  localPort: string;
  tunnelUrl: string;
  token: string;
}

export const DEFAULT_SETTINGS: NamoSettings = {
  mode: "local",
  localIp: typeof window !== 'undefined' ? window.location.hostname : "192.168.0.107",
  localPort: "8000",
  tunnelUrl: "https://api.namonexus.com",
  token: "NamoSovereignToken2026",
};

export function loadSettings(): NamoSettings {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { ...DEFAULT_SETTINGS };
}

export function buildWsUrl(settings: NamoSettings): string {
  const tokenParams = `token=${settings.token || ""}`;
  let baseWs: string;
  if (settings.mode === "tunnel" && settings.tunnelUrl) {
    baseWs = settings.tunnelUrl.replace(/^http/, "ws").replace(/\/$/, "") + "/ws";
  } else {
    baseWs = `ws://${settings.localIp}:${settings.localPort}/ws`;
  }
  return baseWs.includes("?") ? `${baseWs}&${tokenParams}` : `${baseWs}?${tokenParams}`;
}

export function buildHttpUrl(settings: NamoSettings): string {
  if (settings.mode === "tunnel" && settings.tunnelUrl) {
    return settings.tunnelUrl.replace(/\/$/, "");
  }
  return `http://${settings.localIp}:${settings.localPort}`;
}

export function useNamoSettings() {
  const [settings, setSettings] = useState<NamoSettings>(() => loadSettings());

  const saveSettings = useCallback((newSettings: NamoSettings) => {
    setSettings(newSettings);
    localStorage.setItem(LS_KEY, JSON.stringify(newSettings));
  }, []);

  const fetchWithAuth = useCallback(async (url: string, options: RequestInit = {}) => {
    if (settings.token) {
      try {
        // Parse JWT payload (base64url to JSON)
        const parts = settings.token.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
          const exp = payload.exp * 1000;
          const timeLeft = exp - Date.now();
          if (timeLeft < 5 * 60 * 1000 && timeLeft > 0) {
            console.warn("Namo Token is expiring in less than 5 minutes. Please re-authenticate soon.");
            // In a real app, you might trigger a toast notification or auto-refresh here
          }
        }
      } catch (err) {
        // Ignore parsing errors for non-JWT tokens (like 'NamoSovereignToken2026' dev token)
      }
    }

    const headers = new Headers(options.headers || {});
    if (settings.token) {
      headers.set('Authorization', `Bearer ${settings.token}`);
    }

    const response = await fetch(url, { ...options, headers });
    if (response.status === 401 || response.status === 403) {
      console.error("Namo API Authentication Failed: Invalid or expired token");
      alert("เซสชันการใช้งานหมดอายุ หรือ Token ไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่อีกครั้ง");
    }
    return response;
  }, [settings.token]);

  return {
    settings,
    saveSettings,
    wsUrl: buildWsUrl(settings),
    httpUrl: buildHttpUrl(settings),
    fetchWithAuth,
  };
}
