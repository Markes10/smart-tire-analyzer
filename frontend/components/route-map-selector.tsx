"use client"

import { useEffect, useState } from "react"
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents } from "react-leaflet"
import type * as L from "leaflet"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { MapPin, Map, X } from "lucide-react"
import "leaflet/dist/leaflet.css"

interface RouteMapSelectorProps {
    source: string
    destination: string
    onRouteChange: (source: string, destination: string) => void
}

interface MapCoord {
    lat: number
    lng: number
}

function parseMapCoord(value: string): MapCoord | null {
    const [latText, lngText] = value.split(",").map((part) => part.trim())
    const lat = Number(latText)
    const lng = Number(lngText)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
    return { lat, lng }
}

function MapClickHandler({
    mode,
    onLocationSelect,
}: {
    mode: "source" | "destination" | null
    onLocationSelect: (lat: number, lng: number, mode: "source" | "destination") => void
}) {
    useMapEvents({
        click(e: L.LeafletMouseEvent) {
            if (mode) {
                onLocationSelect(e.latlng.lat, e.latlng.lng, mode)
            }
        },
    })
    return null
}

export function RouteMapSelector({
    source,
    destination,
    onRouteChange,
}: RouteMapSelectorProps) {
    const [sourceCoord, setSourceCoord] = useState<MapCoord | null>(null)
    const [destCoord, setDestCoord] = useState<MapCoord | null>(null)
    const [selectMode, setSelectMode] = useState<"source" | "destination" | null>(null)
    const [isClient, setIsClient] = useState(false)
    const [icons, setIcons] = useState<{ defaultIcon?: any; sourceIcon?: any; destIcon?: any }>({})

    useEffect(() => {
        setIsClient(true)
    }, [])

    useEffect(() => {
        setSourceCoord(parseMapCoord(source))
    }, [source])

    useEffect(() => {
        setDestCoord(parseMapCoord(destination))
    }, [destination])

    // Dynamically import leaflet on the client and create marker icons to avoid
    // accessing browser globals during module evaluation at build time.
    useEffect(() => {
        let mounted = true
        if (!isClient) return

        import("leaflet")
            .then((leaflet) => {
                const Llib = (leaflet as any).default || leaflet

                const defaultIcon = Llib.icon({
                    iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
                    iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
                    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41],
                })

                const sourceIcon = Llib.icon({
                    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
                    iconRetinaUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
                    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41],
                })

                const destIcon = Llib.icon({
                    iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
                    iconRetinaUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
                    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41],
                })

                if (mounted) setIcons({ defaultIcon, sourceIcon, destIcon })
            })
            .catch(() => {
                // ignore import errors during build-time or if leaflet is unavailable
            })

        return () => {
            mounted = false
        }
    }, [isClient])

    const handleLocationSelect = (lat: number, lng: number, mode: "source" | "destination") => {
        const locationName = `${lat.toFixed(4)}, ${lng.toFixed(4)}`

        if (mode === "source") {
            setSourceCoord({ lat, lng })
            onRouteChange(locationName, destination)
        } else {
            setDestCoord({ lat, lng })
            onRouteChange(source, locationName)
        }

        setSelectMode(null)
    }

    const clearSource = () => {
        setSourceCoord(null)
        onRouteChange("", destination)
    }

    const clearDestination = () => {
        setDestCoord(null)
        onRouteChange(source, "")
    }

    if (!isClient) {
        return (
            <Card className="border-border/50 bg-card/50">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Map className="h-5 w-5 text-primary" />
                        Route Selection Map
                    </CardTitle>
                    <CardDescription>Select source and destination on the map</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="h-96 flex items-center justify-center bg-muted rounded-lg">
                        Loading map...
                    </div>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card className="border-border/50 bg-card/50">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Map className="h-5 w-5 text-primary" />
                    Route Selection Map
                </CardTitle>
                <CardDescription>Click on the map to select source and destination</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Map Container */}
                <div className="rounded-lg overflow-hidden border border-border/50 h-96">
                    <MapContainer
                        center={[28.6139, 77.2090] as L.LatLngExpression}
                        zoom={12}
                        style={{ height: "100%", width: "100%" }}
                    >
                        <TileLayer
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            attribution="&copy; OpenStreetMap contributors"
                        />
                        {sourceCoord && (
                            <Marker
                                position={[sourceCoord.lat, sourceCoord.lng] as L.LatLngExpression}
                                icon={icons.sourceIcon}
                            >
                                <Popup>Source Location</Popup>
                            </Marker>
                        )}
                        {destCoord && (
                            <Marker
                                position={[destCoord.lat, destCoord.lng] as L.LatLngExpression}
                                icon={icons.destIcon}
                            >
                                <Popup>Destination</Popup>
                            </Marker>
                        )}
                        {sourceCoord && destCoord && (
                            <Polyline
                                positions={[
                                    [sourceCoord.lat, sourceCoord.lng],
                                    [destCoord.lat, destCoord.lng],
                                ] as L.LatLngExpression[]}
                                pathOptions={{ color: "#2563eb", weight: 4, opacity: 0.75 }}
                            />
                        )}
                        <MapClickHandler mode={selectMode} onLocationSelect={handleLocationSelect} />
                    </MapContainer>
                </div>

                {/* Location Selection Controls */}
                <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-green-500" />
                            Source Location
                        </Label>
                        <div className="flex gap-2">
                            <Button
                                onClick={() => setSelectMode(selectMode === "source" ? null : "source")}
                                variant={selectMode === "source" ? "default" : "outline"}
                                className="flex-1"
                                size="sm"
                            >
                                {selectMode === "source" ? "Click on map" : "Select Source"}
                            </Button>
                            {sourceCoord && (
                                <Button
                                    onClick={clearSource}
                                    variant="ghost"
                                    size="sm"
                                    className="px-2"
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                            )}
                        </div>
                        {source && (
                            <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                                {source}
                            </div>
                        )}
                    </div>

                    <div className="space-y-2">
                        <Label className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-red-500" />
                            Destination
                        </Label>
                        <div className="flex gap-2">
                            <Button
                                onClick={() => setSelectMode(selectMode === "destination" ? null : "destination")}
                                variant={selectMode === "destination" ? "default" : "outline"}
                                className="flex-1"
                                size="sm"
                            >
                                {selectMode === "destination" ? "Click on map" : "Select Destination"}
                            </Button>
                            {destCoord && (
                                <Button
                                    onClick={clearDestination}
                                    variant="ghost"
                                    size="sm"
                                    className="px-2"
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                            )}
                        </div>
                        {destination && (
                            <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                                {destination}
                            </div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
