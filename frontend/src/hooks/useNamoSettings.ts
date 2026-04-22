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

  return {
    settings,
    saveSettings,
    wsUrl: buildWsUrl(settings),
    httpUrl: buildHttpUrl(settings),
  };
}
