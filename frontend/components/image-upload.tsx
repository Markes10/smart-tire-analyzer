"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Upload, Camera, X, ImageIcon, Aperture, RotateCcw } from "lucide-react"

interface ImageUploadProps {
  label: string
  description: string
  value: string | null
  onChange: (file: File | null, preview: string | null) => void
}

const ACCEPTED_IMAGE_TYPES = "image/jpeg,image/png,image/webp"
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

export function ImageUpload({ label, description, value, onChange }: ImageUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [isCameraOpen, setIsCameraOpen] = useState(false)
  const [isStartingCamera, setIsStartingCamera] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setIsCameraOpen(false)
    setIsStartingCamera(false)
  }, [])

  useEffect(() => stopCamera, [stopCamera])

  const applyFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) {
      setCameraError("Please choose an image file.")
      return
    }

    if (!ACCEPTED_IMAGE_TYPES.split(",").includes(file.type)) {
      setCameraError("Please choose a JPEG, PNG, or WebP image.")
      return
    }

    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setCameraError("Image is too large. Please choose an image under 10MB.")
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      onChange(file, reader.result as string)
      setCameraError(null)
    }
    reader.readAsDataURL(file)
  }, [onChange])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      applyFile(file)
    }
  }, [applyFile])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      applyFile(file)
    }
    e.target.value = ""
  }, [applyFile])

  const handleRemove = useCallback(() => {
    stopCamera()
    onChange(null, null)
  }, [onChange, stopCamera])

  const openNativeCameraPicker = useCallback(() => {
    cameraInputRef.current?.click()
  }, [])

  const startCamera = useCallback(async () => {
    setCameraError(null)

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError("Live camera preview is not available in this browser. Opening the device camera picker instead.")
      openNativeCameraPicker()
      return
    }

    setIsStartingCamera(true)

    try {
      stopCamera()
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      })

      streamRef.current = stream
      setIsCameraOpen(true)

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
    } catch (error) {
      const message = error instanceof DOMException && error.name === "NotAllowedError"
        ? "Camera permission was denied. Allow camera access or use Browse to upload a tire photo."
        : "Unable to open the camera. You can still use Browse to upload a tire photo."
      setCameraError(message)
    } finally {
      setIsStartingCamera(false)
    }
  }, [openNativeCameraPicker, stopCamera])

  const capturePhoto = useCallback(() => {
    const video = videoRef.current
    if (!video || !streamRef.current) return

    const width = video.videoWidth || 1280
    const height = video.videoHeight || 720
    const canvas = document.createElement("canvas")
    canvas.width = width
    canvas.height = height

    const context = canvas.getContext("2d")
    if (!context) {
      setCameraError("Unable to capture the camera frame. Please try again.")
      return
    }

    context.drawImage(video, 0, 0, width, height)
    canvas.toBlob((blob) => {
      if (!blob) {
        setCameraError("Unable to save the captured photo. Please try again.")
        return
      }

      const safeLabel = label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
      const file = new File([blob], `${safeLabel || "tire"}-${Date.now()}.jpg`, {
        type: "image/jpeg",
      })

      applyFile(file)
      stopCamera()
    }, "image/jpeg", 0.92)
  }, [applyFile, label, stopCamera])

  return (
    <Card className={`overflow-hidden border-border/50 bg-card/50 transition-all ${isDragOver ? "border-primary bg-primary/5" : ""
      }`}>
      <CardContent className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="font-medium text-foreground">{label}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          {value && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              onClick={handleRemove}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {isCameraOpen ? (
          <div className="space-y-3">
            <div className="relative aspect-video overflow-hidden rounded-lg bg-neutral-950">
              <video
                ref={videoRef}
                aria-label={`${label} live camera preview`}
                autoPlay
                muted
                playsInline
                className="h-full w-full object-cover"
              />
              <div className="pointer-events-none absolute inset-0 border border-white/20" />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <Button type="button" className="gap-2" onClick={capturePhoto}>
                <Aperture className="h-4 w-4" />
                Capture Photo
              </Button>
              <Button type="button" variant="outline" className="gap-2" onClick={stopCamera}>
                <X className="h-4 w-4" />
                Cancel
              </Button>
            </div>
          </div>
        ) : value ? (
          <div className="relative aspect-video overflow-hidden rounded-lg bg-muted">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={value}
              alt={label}
              className="h-full w-full object-cover"
            />
          </div>
        ) : (
          <>
          <button
            type="button"
            className="flex w-full cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border bg-muted/30 p-6 transition-colors hover:border-primary/50 hover:bg-muted/50"
            aria-label={`${label} image dropzone`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <ImageIcon className="h-6 w-6 text-primary" />
            </div>
            <div className="mt-4 text-center">
              <p className="text-sm font-medium text-foreground">
                Drop image here or click to upload
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                JPEG, PNG, or WebP up to 10MB
              </p>
            </div>
          </button>
            <div className="mt-4 flex justify-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="gap-1.5"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-3.5 w-3.5" />
                Browse
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="gap-1.5"
                disabled={isStartingCamera}
                onClick={startCamera}
              >
                {isStartingCamera ? (
                  <RotateCcw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Camera className="h-3.5 w-3.5" />
                )}
                {isStartingCamera ? "Opening…" : "Camera"}
              </Button>
            </div>
            {cameraError && (
              <p className="mt-3 max-w-sm text-center text-xs text-destructive">
                {cameraError}
              </p>
            )}
          </>
        )}
        {cameraError && (value || isCameraOpen) && (
          <p className="mt-3 text-xs text-destructive">{cameraError}</p>
        )}
        {!isCameraOpen && value && (
          <div className="mt-3 flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="secondary" className="gap-1.5" onClick={() => fileInputRef.current?.click()}>
              <Upload className="h-3.5 w-3.5" />
              Replace
            </Button>
            <Button type="button" size="sm" variant="outline" className="gap-1.5" onClick={startCamera}>
              <Camera className="h-3.5 w-3.5" />
              Retake
            </Button>
          </div>
        )}
        <input
          ref={fileInputRef}
          type="file"
          aria-label={`${label} image upload`}
          accept={ACCEPTED_IMAGE_TYPES}
          className="hidden"
          onChange={handleFileSelect}
        />
        <input
          ref={cameraInputRef}
          type="file"
          aria-label={`${label} camera upload`}
          accept={ACCEPTED_IMAGE_TYPES}
          capture="environment"
          className="hidden"
          onChange={handleFileSelect}
        />
      </CardContent>
    </Card>
  )
}
