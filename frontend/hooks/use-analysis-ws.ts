"use client"

import { useEffect, useRef, useCallback } from "react"

type WsMessage = {
  type: string
  session_id?: string
  step?: string
  progress?: number
  payload?: unknown
}

export function useAnalysisWebSocket(
  sessionId: string | null,
  onProgress?: (progress: number, step: string) => void,
  onComplete?: (payload: unknown) => void,
) {
  const wsRef = useRef<WebSocket | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const connect = useCallback(() => {
    if (!sessionId) return
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const wsUrl = baseUrl.replace(/^http/, "ws") + `/ws/analysis/${sessionId}`
    
    try {
      const ws = new WebSocket(wsUrl)
      ws.onopen = () => {
        pingRef.current = setInterval(() => ws.send("ping"), 30000)
      }
      ws.onmessage = (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data)
          if (msg.type === "progress" && onProgress) {
            onProgress(msg.progress || 0, msg.step || "")
          } else if (msg.type === "complete" && onComplete) {
            onComplete(msg.payload)
          }
        } catch { /* ignore parse errors */ }
      }
      ws.onclose = () => {
        if (pingRef.current) clearInterval(pingRef.current)
      }
      wsRef.current = ws
    } catch { /* ignore connection errors */ }
  }, [sessionId, onProgress, onComplete])

  useEffect(() => {
    connect()
    return () => {
      if (pingRef.current) clearInterval(pingRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  return { disconnect: () => wsRef.current?.close() }
}
