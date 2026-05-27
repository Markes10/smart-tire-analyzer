"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Search,
  Plus,
  Truck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  BarChart3,
  Upload,
  Filter,
  MoreHorizontal,
  Car
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

// Mock fleet data
const fleetVehicles = [
  {
    id: "VEH-001",
    name: "Delivery Van #1",
    type: "Van",
    tires: [
      { position: "FL", score: 85, status: "good" },
      { position: "FR", score: 82, status: "good" },
      { position: "RL", score: 68, status: "warning" },
      { position: "RR", score: 72, status: "warning" },
    ],
    lastChecked: "2026-05-08",
    nextService: "2026-05-25",
    status: "attention",
  },
  {
    id: "VEH-002",
    name: "Delivery Van #2",
    type: "Van",
    tires: [
      { position: "FL", score: 92, status: "good" },
      { position: "FR", score: 90, status: "good" },
      { position: "RL", score: 88, status: "good" },
      { position: "RR", score: 91, status: "good" },
    ],
    lastChecked: "2026-05-09",
    nextService: "2026-06-15",
    status: "healthy",
  },
  {
    id: "VEH-003",
    name: "Service Truck",
    type: "Truck",
    tires: [
      { position: "FL", score: 45, status: "critical" },
      { position: "FR", score: 52, status: "warning" },
      { position: "RL", score: 58, status: "warning" },
      { position: "RR", score: 48, status: "critical" },
    ],
    lastChecked: "2026-05-10",
    nextService: "2026-05-12",
    status: "critical",
  },
  {
    id: "VEH-004",
    name: "Company Car #1",
    type: "Sedan",
    tires: [
      { position: "FL", score: 78, status: "good" },
      { position: "FR", score: 75, status: "good" },
      { position: "RL", score: 80, status: "good" },
      { position: "RR", score: 77, status: "good" },
    ],
    lastChecked: "2026-05-05",
    nextService: "2026-06-01",
    status: "healthy",
  },
]

const fleetStats = {
  totalVehicles: 4,
  totalTires: 16,
  healthyCount: 2,
  attentionCount: 1,
  criticalCount: 1,
  avgScore: 74,
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case "healthy": return <CheckCircle2 className="h-4 w-4 text-success" />
    case "attention": return <Clock className="h-4 w-4 text-warning" />
    case "critical": return <AlertTriangle className="h-4 w-4 text-critical" />
    default: return null
  }
}

const getStatusBadgeVariant = (status: string) => {
  switch (status) {
    case "healthy": return "default"
    case "attention": return "secondary"
    case "critical": return "destructive"
    default: return "secondary"
  }
}

const getTireColor = (score: number) => {
  if (score >= 80) return "bg-success"
  if (score >= 60) return "bg-warning"
  return "bg-critical"
}

export default function FleetPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [activeTab, setActiveTab] = useState("overview")

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Fleet Management
              </h1>
              <p className="mt-1 text-muted-foreground">
                Monitor and manage tire health across your fleet
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="gap-1.5">
                <Upload className="h-4 w-4" />
                Bulk Upload
              </Button>
              <Button className="gap-1.5">
                <Plus className="h-4 w-4" />
                Add Vehicle
              </Button>
            </div>
          </div>

          {/* Stats Overview */}
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Truck className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-foreground">{fleetStats.totalVehicles}</div>
                  <div className="text-sm text-muted-foreground">Vehicles</div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <BarChart3 className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-foreground">{fleetStats.avgScore}</div>
                  <div className="text-sm text-muted-foreground">Avg Score</div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
                  <CheckCircle2 className="h-5 w-5 text-success" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-success">{fleetStats.healthyCount}</div>
                  <div className="text-sm text-muted-foreground">Healthy</div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10">
                  <Clock className="h-5 w-5 text-warning" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-warning">{fleetStats.attentionCount}</div>
                  <div className="text-sm text-muted-foreground">Attention</div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-critical/10">
                  <AlertTriangle className="h-5 w-5 text-critical" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-critical">{fleetStats.criticalCount}</div>
                  <div className="text-sm text-muted-foreground">Critical</div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="vehicles">Vehicles</TabsTrigger>
                <TabsTrigger value="alerts">Alerts</TabsTrigger>
              </TabsList>
              <div className="flex gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search vehicles..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-50 pl-9"
                  />
                </div>
                <Button variant="outline" size="icon">
                  <Filter className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <TabsContent value="overview" className="space-y-6">
              {/* Fleet Health Overview */}
              <Card className="border-border/50 bg-card/50">
                <CardHeader>
                  <CardTitle>Fleet Health Distribution</CardTitle>
                  <CardDescription>Tire condition across all vehicles</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center gap-4">
                      <span className="w-20 text-sm text-muted-foreground">Healthy</span>
                      <Progress value={(fleetStats.healthyCount / fleetStats.totalVehicles) * 100} className="flex-1 h-3" />
                      <span className="w-12 text-right text-sm text-foreground">{fleetStats.healthyCount}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="w-20 text-sm text-muted-foreground">Attention</span>
                      <Progress value={(fleetStats.attentionCount / fleetStats.totalVehicles) * 100} className="flex-1 h-3" />
                      <span className="w-12 text-right text-sm text-foreground">{fleetStats.attentionCount}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="w-20 text-sm text-muted-foreground">Critical</span>
                      <Progress value={(fleetStats.criticalCount / fleetStats.totalVehicles) * 100} className="flex-1 h-3" />
                      <span className="w-12 text-right text-sm text-foreground">{fleetStats.criticalCount}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Vehicle Cards */}
              <div className="grid gap-4 md:grid-cols-2">
                {fleetVehicles.map((vehicle) => (
                  <Card key={vehicle.id} className="border-border/50 bg-card/50">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                            <Car className="h-5 w-5 text-muted-foreground" />
                          </div>
                          <div>
                            <CardTitle className="text-base">{vehicle.name}</CardTitle>
                            <CardDescription className="text-xs">{vehicle.id}</CardDescription>
                          </div>
                        </div>
                        <Badge variant={getStatusBadgeVariant(vehicle.status)}>
                          {getStatusIcon(vehicle.status)}
                          <span className="ml-1 capitalize">{vehicle.status}</span>
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {/* Tire Grid */}
                      <div className="mb-4 grid grid-cols-2 gap-3">
                        {vehicle.tires.map((tire) => (
                          <div
                            key={tire.position}
                            className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 px-3 py-2"
                          >
                            <span className="text-xs font-medium text-muted-foreground">
                              {tire.position}
                            </span>
                            <div className="flex items-center gap-2">
                              <div className={`h-2 w-2 rounded-full ${getTireColor(tire.score)}`} />
                              <span className="text-sm font-medium text-foreground">{tire.score}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Last: {new Date(vehicle.lastChecked).toLocaleDateString()}</span>
                        <span>Next: {new Date(vehicle.nextService).toLocaleDateString()}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="vehicles">
              <Card className="border-border/50 bg-card/50">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Vehicle</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Avg Score</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Checked</TableHead>
                      <TableHead>Next Service</TableHead>
                      <TableHead className="w-12.5"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fleetVehicles.map((vehicle) => {
                      const avgScore = Math.round(
                        vehicle.tires.reduce((sum, t) => sum + t.score, 0) / vehicle.tires.length
                      )
                      return (
                        <TableRow key={vehicle.id}>
                          <TableCell>
                            <div>
                              <div className="font-medium text-foreground">{vehicle.name}</div>
                              <div className="text-xs text-muted-foreground">{vehicle.id}</div>
                            </div>
                          </TableCell>
                          <TableCell>{vehicle.type}</TableCell>
                          <TableCell>
                            <span className={avgScore >= 70 ? "text-success" : avgScore >= 50 ? "text-warning" : "text-critical"}>
                              {avgScore}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge variant={getStatusBadgeVariant(vehicle.status)}>
                              {vehicle.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{new Date(vehicle.lastChecked).toLocaleDateString()}</TableCell>
                          <TableCell>{new Date(vehicle.nextService).toLocaleDateString()}</TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem>View Details</DropdownMenuItem>
                                <DropdownMenuItem>Analyze Tires</DropdownMenuItem>
                                <DropdownMenuItem>Edit Vehicle</DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </Card>
            </TabsContent>

            <TabsContent value="alerts">
              <Card className="border-border/50 bg-card/50">
                <CardHeader>
                  <CardTitle>Active Alerts</CardTitle>
                  <CardDescription>Vehicles requiring immediate attention</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-start gap-4 rounded-lg border border-critical/50 bg-critical/5 p-4">
                      <AlertTriangle className="h-5 w-5 text-critical" />
                      <div className="flex-1">
                        <h4 className="font-medium text-foreground">Critical Tire Condition</h4>
                        <p className="mt-1 text-sm text-muted-foreground">
                          Service Truck (VEH-003) has 2 tires below safe threshold. Immediate replacement recommended.
                        </p>
                        <div className="mt-3 flex gap-2">
                          <Button size="sm" variant="destructive">Schedule Service</Button>
                          <Button size="sm" variant="outline">View Details</Button>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-start gap-4 rounded-lg border border-warning/50 bg-warning/5 p-4">
                      <Clock className="h-5 w-5 text-warning" />
                      <div className="flex-1">
                        <h4 className="font-medium text-foreground">Maintenance Due Soon</h4>
                        <p className="mt-1 text-sm text-muted-foreground">
                          Delivery Van #1 (VEH-001) rear tires showing increased wear. Schedule rotation within 2 weeks.
                        </p>
                        <div className="mt-3 flex gap-2">
                          <Button size="sm" variant="secondary">Schedule Rotation</Button>
                          <Button size="sm" variant="outline">Dismiss</Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </main>
      <Footer />
    </div>
  )
}
