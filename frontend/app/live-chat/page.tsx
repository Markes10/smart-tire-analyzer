"use client"

import { useState, useRef, useEffect } from "react"
import { Header } from "@/components/header"
import { Footer } from "@/components/footer"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { MessageSquare, Send, Bot, User, Clock, CheckCircle2 } from "lucide-react"

type Message = {
    id: string
    sender: "user" | "agent"
    text: string
    timestamp: Date
}

const initialMessages: Message[] = [
    {
        id: "welcome",
        sender: "agent",
        text: "Hello! Welcome to Smart Tire Analyzer support. How can I help you today?",
        timestamp: new Date(),
    },
]

const quickReplies = [
    "How do I analyze a tire?",
    "I need help with my account",
    "What are the pricing plans?",
    "I have a technical issue",
]

export default function LiveChatPage() {
    const [messages, setMessages] = useState<Message[]>(initialMessages)
    const [inputValue, setInputValue] = useState("")
    const [isTyping, setIsTyping] = useState(false)
    const [modelLabel, setModelLabel] = useState("Hosted AI")
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSend = async (text?: string) => {
        const messageText = text || inputValue
        if (!messageText.trim() || isTyping) return

        const userMessage: Message = {
            id: crypto.randomUUID(),
            sender: "user",
            text: messageText,
            timestamp: new Date(),
        }
        const nextMessages = [...messages, userMessage]

        setMessages(nextMessages)
        setInputValue("")
        setIsTyping(true)

        try {
            const response = await fetch("/api/live-chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    messages: nextMessages.map((message) => ({
                        role: message.sender === "agent" ? "assistant" : "user",
                        content: message.text,
                    })),
                }),
            })

            const data = await response.json().catch(() => null)

            if (!response.ok) {
                throw new Error(data?.error || "The live chat assistant is unavailable right now.")
            }

            if (typeof data?.model === "string" && data.model.trim()) {
                setModelLabel(data.model)
            }

            const agentMessage: Message = {
                id: crypto.randomUUID(),
                sender: "agent",
                text: data.reply,
                timestamp: new Date(),
            }
            setMessages((prev) => [...prev, agentMessage])
        } catch (error) {
            const agentMessage: Message = {
                id: crypto.randomUUID(),
                sender: "agent",
                text: error instanceof Error
                    ? error.message
                    : "The live chat assistant is unavailable right now.",
                timestamp: new Date(),
            }
            setMessages((prev) => [...prev, agentMessage])
        } finally {
            setIsTyping(false)
        }
    }

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }

    return (
        <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1 pt-16">
                {/* Hero Section */}
                <section className="border-b border-border/50 py-12">
                    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                        <div className="flex items-center gap-4">
                            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
                                <MessageSquare className="h-7 w-7 text-primary" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-bold tracking-tight text-foreground">
                                    Live Chat Support
                                </h1>
                                <p className="text-muted-foreground">
                                    Get instant help from our support team
                                </p>
                            </div>
                            <Badge variant="outline" className="ml-auto border-green-500/50 text-green-600">
                                <span className="mr-1.5 h-2 w-2 rounded-full bg-green-500" />
                                Online
                            </Badge>
                        </div>
                    </div>
                </section>

                {/* Chat Section */}
                <section className="py-12">
                    <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
                        <Card className="border-border/50 bg-card/50">
                            <CardHeader className="border-b border-border/50">
                                <div className="flex items-center gap-3">
                                    <Avatar>
                                        <AvatarImage src="/team-shivam-bandekar.jpg" />
                                        <AvatarFallback>ST</AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <CardTitle className="text-base">Smart Tire Assistant</CardTitle>
                                        <p className="text-sm text-muted-foreground">
                                            Powered by {modelLabel}
                                        </p>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                {/* Messages */}
                                <div className="h-100 overflow-y-auto p-4">
                                    <div className="space-y-4">
                                        {messages.map((message) => (
                                            <div
                                                key={message.id}
                                                className={`flex gap-3 ${message.sender === "user" ? "flex-row-reverse" : ""
                                                    }`}
                                            >
                                                <div
                                                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${message.sender === "agent"
                                                        ? "bg-primary/10"
                                                        : "bg-muted"
                                                        }`}
                                                >
                                                    {message.sender === "agent" ? (
                                                        <Bot className="h-4 w-4 text-primary" />
                                                    ) : (
                                                        <User className="h-4 w-4 text-muted-foreground" />
                                                    )}
                                                </div>
                                                <div
                                                    className={`max-w-[75%] space-y-1 ${message.sender === "user" ? "text-right" : ""
                                                        }`}
                                                >
                                                    <div
                                                        className={`inline-block rounded-2xl px-4 py-2 ${message.sender === "agent"
                                                            ? "bg-muted text-foreground"
                                                            : "bg-primary text-primary-foreground"
                                                            }`}
                                                    >
                                                        <p className="text-sm">{message.text}</p>
                                                    </div>
                                                    <p className="text-xs text-muted-foreground">
                                                        {formatTime(message.timestamp)}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                        {isTyping && (
                                            <div className="flex gap-3">
                                                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                                                    <Bot className="h-4 w-4 text-primary" />
                                                </div>
                                                <div className="inline-block rounded-2xl bg-muted px-4 py-2">
                                                    <div className="flex gap-1">
                                                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50" />
                                                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0.1s]" />
                                                        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0.2s]" />
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                        <div ref={messagesEndRef} />
                                    </div>
                                </div>

                                {/* Quick Replies */}
                                <div className="border-t border-border/50 px-4 py-3">
                                    <div className="flex flex-wrap gap-2">
                                        {quickReplies.map((reply) => (
                                            <Button
                                                key={reply}
                                                variant="outline"
                                                size="sm"
                                                className="text-xs"
                                                disabled={isTyping}
                                                onClick={() => handleSend(reply)}
                                            >
                                                {reply}
                                            </Button>
                                        ))}
                                    </div>
                                </div>

                                {/* Input */}
                                <div className="border-t border-border/50 p-4">
                                    <form
                                        onSubmit={(e) => {
                                            e.preventDefault()
                                            handleSend()
                                        }}
                                        className="flex gap-2"
                                    >
                                        <Input
                                            value={inputValue}
                                            onChange={(e) => setInputValue(e.target.value)}
                                            placeholder="Type your message..."
                                            className="flex-1"
                                            disabled={isTyping}
                                        />
                                        <Button type="submit" size="icon" disabled={isTyping}>
                                            <Send className="h-4 w-4" />
                                            <span className="sr-only">Send message</span>
                                        </Button>
                                    </form>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Info Cards */}
                        <div className="mt-8 grid gap-4 sm:grid-cols-2">
                            <Card className="border-border/50 bg-card/50">
                                <CardContent className="flex items-center gap-4 p-4">
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                                        <Clock className="h-5 w-5 text-primary" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-foreground">Business Hours</h3>
                                        <p className="text-sm text-muted-foreground">
                                            Mon-Fri: 8am - 6pm PST
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                            <Card className="border-border/50 bg-card/50">
                                <CardContent className="flex items-center gap-4 p-4">
                                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                                        <CheckCircle2 className="h-5 w-5 text-primary" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-foreground">Response Time</h3>
                                        <p className="text-sm text-muted-foreground">
                                            Average: Under 2 minutes
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    )
}
