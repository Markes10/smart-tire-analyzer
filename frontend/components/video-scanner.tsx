"use client"

import { useRef, useState, useCallback } from "react"

type ScanResult = {
  frame_id: number
  predictions?: any
  smoothed?: any
  error?: string
}

export function VideoScanner() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [results, setResults] = useState<ScanResult[]>([])
  const [streaming, setStreaming] = useState(false)

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setStreaming(true)
    } catch (err) {
      console.error("Camera access denied:", err)
    }
  }, [])

  const startScanning = useCallback(() => {
    if (!streaming) return
    
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const wsUrl = baseUrl.replace(/^http/, "ws") + "/video/stream"
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => setIsScanning(true)
    ws.onmessage = (event) => {
      try {
        const result: ScanResult = JSON.parse(event.data)
        setResults(prev => [...prev.slice(-20), result])
      } catch { /* ignore parse errors */ }
    }
    ws.onclose = () => setIsScanning(false)
    wsRef.current = ws
    
    const canvas = document.createElement("canvas")
    canvas.width = 224
    canvas.height = 224
    const ctx = canvas.getContext("2d")
    
    const capture = () => {
      if (ws.readyState !== WebSocket.OPEN) return
      if (videoRef.current && ctx) {
        ctx.drawImage(videoRef.current, 0, 0, 224, 224)
        canvas.toBlob((blob) => {
          if (blob && ws.readyState === WebSocket.OPEN) {
            blob.arrayBuffer().then(buf => ws.send(buf))
          }
        }, "image/jpeg", 0.8)
      }
      scanTimer = requestAnimationFrame(capture)
    }
    
    let scanTimer = requestAnimationFrame(capture)
    
    return () => {
      cancelAnimationFrame(scanTimer)
      ws.close()
    }
  }, [streaming])

  const stopScanning = useCallback(() => {
    wsRef.current?.close()
    setIsScanning(false)
  }, [])

  return { videoRef, isScanning, streaming, results, startCamera, startScanning, stopScanning }
}
