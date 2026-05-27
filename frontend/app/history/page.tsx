"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { getAnalysisHistory, type HistoryItem } from "@/lib/analyze"
import {
  ArrowRight,
  BarChart3,
  Calendar,
  ChevronRight,
  Gauge,
  RefreshCcw,
  Search,
  TrendingDown,
  TrendingUp,
} from "lucide-react"

function getScoreColor(score: number) {
  if (score >= 8) return "text-success"
  if (score >= 6) return "text-chart-3"
  if (score >= 4) return "text-warning"
  return "text-critical"
}

function riskBadgeVariant(risk: string | null) {
  if (risk === "HIGH" || risk === "CRITICAL") return "destructive"
  if (risk === "MODERATE") return "secondary"
  return "default"
}

function displayDate(value: string | null) {
  if (!value) return "Unknown date"
  return new Date(value).toLocaleDateString()
}

export default function HistoryPage() {
  const [records, setRecords] = useState<HistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState("")
  const [sortBy, setSortBy] = useState("date")
  const [riskFilter, setRiskFilter] = useState("all")
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadHistory() {
      setIsLoading(true)
      setError(null)
      try {
        const data = await getAnalysisHistory({
          page,
          pageSize: 20,
          riskLevel: riskFilter === "all" ? undefined : riskFilter,
        })
        if (!mounted) return
        setRecords((current) => page === 1 ? data.results : [...current, ...data.results])
        setTotal(data.total)
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Could not load analysis history.")
      } finally {
        if (mounted) setIsLoading(false)
      }
    }

    loadHistory()
    return () => {
      mounted = false
    }
  }, [page, riskFilter])

  const filteredRecords = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    const filtered = records.filter((record) => {
      if (!query) return true
      return [
        record.session_id,
        record.risk_level,
        record.wear_pattern,
      ].some((value) => String(value ?? "").toLowerCase().includes(query))
    })

    return [...filtered].sort((a, b) => {
      if (sortBy === "score") return (b.health_score ?? 0) - (a.health_score ?? 0)
      if (sortBy === "depth") return (b.avg_tread_mm ?? 0) - (a.avg_tread_mm ?? 0)
      return new Date(b.timestamp ?? 0).getTime() - new Date(a.timestamp ?? 0).getTime()
    })
  }, [records, searchQuery, sortBy])

  const latestScore = records[0]?.health_score ?? 0
  const previousScore = records[1]?.health_score ?? latestScore
  const scoreDiff = latestScore - previousScore

  const refresh = () => {
    setRecords([])
    setPage(1)
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1 pt-16">
        <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Analysis History
              </h1>
              <p className="mt-1 text-muted-foreground">Track real tire analysis results saved by the backend</p>
            </div>
            <Button variant="outline" size="sm" className="gap-2" onClick={refresh}>
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </Button>
          </div>

          <div className="mb-8 grid gap-4 sm:grid-cols-3">
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <BarChart3 className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-foreground">{total}</div>
                  <div className="text-sm text-muted-foreground">Total Analyses</div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <Gauge className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <div className={`text-2xl font-bold ${getScoreColor(latestScore)}`}>
                    {latestScore ? latestScore.toFixed(1) : "--"}
                  </div>
                  <div className="text-sm text-muted-foreground">Current Score</div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  {scoreDiff >= 0 ? (
                    <TrendingUp className="h-6 w-6 text-success" />
                  ) : (
                    <TrendingDown className="h-6 w-6 text-critical" />
                  )}
                </div>
                <div>
                  <div className={`text-2xl font-bold ${scoreDiff >= 0 ? "text-success" : "text-critical"}`}>
                    {records.length > 1 ? `${scoreDiff > 0 ? "+" : ""}${scoreDiff.toFixed(1)}` : "--"}
                  </div>
                  <div className="text-sm text-muted-foreground">Change from Last</div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative flex-1 sm:max-w-xs">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by ID, risk, or wear..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Select
                value={riskFilter}
                onValueChange={(value) => {
                  setRecords([])
                  setPage(1)
                  setRiskFilter(value)
                }}
              >
                <SelectTrigger className="w-35">
                  <SelectValue placeholder="Risk" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All risks</SelectItem>
                  <SelectItem value="LOW">Low</SelectItem>
                  <SelectItem value="MODERATE">Moderate</SelectItem>
                  <SelectItem value="HIGH">High</SelectItem>
                  <SelectItem value="CRITICAL">Critical</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-35">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="date">Date</SelectItem>
                  <SelectItem value="score">Score</SelectItem>
                  <SelectItem value="depth">Tread Depth</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {error && (
            <Card className="mb-6 border-destructive/50 bg-destructive/5">
              <CardContent className="py-4 text-sm text-destructive">{error}</CardContent>
            </Card>
          )}

          <div className="space-y-4">
            {filteredRecords.map((analysis, index) => {
              const previous = filteredRecords[index + 1]
              const trend = previous?.health_score == null || analysis.health_score == null
                ? "stable"
                : analysis.health_score < previous.health_score
                  ? "down"
                  : analysis.health_score > previous.health_score
                    ? "up"
                    : "stable"

              return (
                <Card
                  key={analysis.session_id}
                  className="border-border/50 bg-card/50 transition-all hover:border-primary/50"
                >
                  <CardContent className="flex items-center justify-between gap-4 py-4">
                    <div className="flex min-w-0 items-center gap-4 sm:gap-6">
                      <div className="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-lg bg-muted">
                        <span className={`text-lg font-bold ${getScoreColor(analysis.health_score ?? 0)}`}>
                          {analysis.health_score?.toFixed(1) ?? "--"}
                        </span>
                      </div>

                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="font-medium text-foreground">
                            {analysis.wear_pattern?.replaceAll("_", " ") ?? "Unknown wear"}
                          </span>
                          <Badge variant={riskBadgeVariant(analysis.risk_level)}>
                            {analysis.risk_level ?? "UNKNOWN"}
                          </Badge>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" />
                            {displayDate(analysis.timestamp)}
                          </span>
                          <span>Tread: {analysis.avg_tread_mm?.toFixed(2) ?? "--"}mm</span>
                          <span className="max-w-55 truncate font-mono text-xs">{analysis.session_id}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 sm:gap-4">
                      <div className="hidden items-center gap-1 sm:flex">
                        {trend === "down" ? (
                          <TrendingDown className="h-4 w-4 text-critical" />
                        ) : trend === "up" ? (
                          <TrendingUp className="h-4 w-4 text-success" />
                        ) : (
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                      <Button variant="ghost" size="sm" className="gap-1" asChild>
                        <Link href={`/analyze/results?id=${encodeURIComponent(analysis.session_id)}`}>
                          View
                          <ChevronRight className="h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {!isLoading && filteredRecords.length === 0 && (
            <Card className="border-border/50 bg-card/50">
              <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
                <p className="text-muted-foreground">No analysis history found.</p>
                <Button asChild>
                  <Link href="/analyze">Analyze a Tire</Link>
                </Button>
              </CardContent>
            </Card>
          )}

          {isLoading && (
            <div className="mt-8 text-center text-sm text-muted-foreground">Loading history...</div>
          )}

          {records.length < total && !isLoading && (
            <div className="mt-8 flex justify-center">
              <Button variant="outline" onClick={() => setPage((current) => current + 1)}>
                Load More
              </Button>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}
