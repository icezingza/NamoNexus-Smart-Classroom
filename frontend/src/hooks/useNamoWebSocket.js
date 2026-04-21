import { useState, useEffect, useRef, useCallback } from "react";

export function useNamoWebSocket(url) {
    const [isConnected, setIsConnected] = useState(false);
    const [serverState, setServerState] = useState(null);

    const wsRef = useRef(null);
    const reconnectAttempts = useRef(0);
    const pingIntervalRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    const connect = useCallback(() => {
        // ป้องกันการต่อซ้ำถ้าสถานะยังเชื่อมต่ออยู่
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("[WS] Connected to", url);
            setIsConnected(true);
            reconnectAttempts.current = 0; // รีเซ็ตจำนวนครั้งที่พยายามเชื่อมต่อใหม่

            // เริ่มส่ง Ping ทุกๆ 30 วินาที เพื่อรักษาการเชื่อมต่อ Cloudflare Tunnel
            pingIntervalRef.current = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send("ping");
                }
            }, 30000);
        };

        ws.onmessage = (event) => {
            // เพิกเฉยต่อข้อความ pong ที่เซิร์ฟเวอร์ตอบกลับมา
            if (event.data === "pong") return;

            try {
                const data = JSON.parse(event.data);
                setServerState(data);
            } catch (err) {
                console.error("[WS] Failed to parse message:", err);
            }
        };

        ws.onclose = (event) => {
            console.warn(`[WS] Disconnected (Code: ${event.code})`);
            setIsConnected(false);
            cleanup();
            scheduleReconnect();
        };

        ws.onerror = (error) => {
            console.error("[WS] Error occurred");
            ws.close(); // บังคับปิดเพื่อกระตุ้นให้ onclose ทำงานและเริ่มการ reconnect
        };
    }, [url]);

    const scheduleReconnect = useCallback(() => {
        // Exponential Backoff: หน่วงเวลา 1s, 2s, 4s, 8s... สูงสุดที่ 15 วินาที
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 15000);
        console.log(`[WS] Reconnecting in ${delay / 1000} seconds...`);

        reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current += 1;
            connect();
        }, delay);
    }, [connect]);

    const cleanup = () => {
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };

    useEffect(() => {
        connect();
        return () => {
            cleanup();
            if (wsRef.current) wsRef.current.close();
        };
    }, [connect]);

    return { isConnected, serverState };
}