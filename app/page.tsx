/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

import { useState, useEffect, useRef } from "react"
import { Input } from "@/components/ui/input"

import Image from "next/image"
import { useWallet } from "@suiet/wallet-kit"
import { ArrowUp } from "lucide-react"
import { getWalletBalance } from "./sui/client"

interface Message {
  role: "user" | "assistant"
  content: string | Strategy[]
  type: "text" | "strategies"
}

interface Strategy {
  id: string
  name: string
  description: string
  symbol: string
  minimumAmount: number
  returns: number
}

const cryptoLogos: any = {
  "BTC": "https://cryptologos.cc/logos/bitcoin-btc-logo.svg",
  "ETH": "https://cryptologos.cc/logos/ethereum-eth-logo.svg",
  "ADA": "https://cryptologos.cc/logos/cardano-ada-logo.svg",
  "SOL": "https://cryptologos.cc/logos/solana-sol-logo.svg",
  "DOT": "https://cryptologos.cc/logos/polkadot-new-dot-logo.svg",
  "DOGE": "https://cryptologos.cc/logos/dogecoin-doge-logo.svg",
  "LUNA": "https://cryptologos.cc/logos/terra-luna-luna-logo.svg",
  "AVAX": "https://cryptologos.cc/logos/avalanche-avax-logo.svg",
  "UNI": "https://cryptologos.cc/logos/uniswap-uni-logo.svg",
  "LINK": "https://cryptologos.cc/logos/chainlink-link-logo.svg",
  "SUI": "https://cryptologos.cc/logos/sui-sui-logo.svg"
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [usdcBalance, setUsdcBalance] = useState<number>(0)
  const [isLoading, setIsLoading] = useState(false)
  const wallet = useWallet()
  const [error, setError] = useState<string | null>(null)
  const [currentTypingMessage, setCurrentTypingMessage] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const getUSDCBalance = async () => {
    const balance = await getWalletBalance(wallet.address as string)
    setUsdcBalance(balance)
  }

  useEffect(() => {
    if (wallet && wallet.connected) getUSDCBalance()
  }, [wallet.connected])
  // Function to scroll to the latest message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, currentTypingMessage])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() === "") return

    setIsLoading(true)
    setError(null)
    const walletAddress = wallet?.account?.address
    console.log("USDC Balance:", usdcBalance)
    const userInput = 
    `
    USER WALLET STATUS: ${walletAddress ? "CONNECTED" : "NOT CONNECTED"}
    ${walletAddress ? `USER WALLET ADDRESS: ${walletAddress}` : ""}
    ${walletAddress ? `USER USDC BALANCE: ${100000000}` : ""}
    USER SAID: ${input}
    `
    console.log("User input:", userInput)
    const userMessage: Message = { role: "user", content: userInput, type: "text" }
    const conversationMessage: Message = { role: "user", content: input, type: "text" }
    setMessages((prev) => [...prev, conversationMessage])
    setInput("")

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ messages: [...messages, userMessage] }),
      })

      if (!response.ok) {
        throw new Error("Failed to fetch response")
      }

      const data = await response.json()
      setCurrentTypingMessage("")
      processMessageResponse(data)
    } catch (error) {
      console.error("Error:", error)
      setError("Failed to get a response")
    } finally {
      setIsLoading(false)
    }
  }

  const processMessageResponse = (data: { type: string; content: string | Strategy[] }) => {
    if (data.type === "text") {
      typeMessage(data.content as string)
    } else if (data.type === "strategies") {
      setMessages((prev) => [...prev, { role: "assistant", content: data.content as Strategy[], type: "strategies" }])
      setCurrentTypingMessage(null)
    }
  }

  const typeMessage = (fullMessage: string) => {
    let index = 0
    const typingInterval = setInterval(() => {
      if (index < fullMessage.length) {
        setCurrentTypingMessage(fullMessage.slice(0, index + 1))
        index++
      } else {
        clearInterval(typingInterval)
        setMessages((prev) => [...prev, { role: "assistant", content: fullMessage, type: "text" }])
        setCurrentTypingMessage(null)
      }
    }, 10) // Adjust typing speed here
  }


  const renderStrategies = (strategies: Strategy[]) => {
    return strategies.map((strategy, index) => (
      <div key={`strategy-${index + 1}`} className="w-60 min-w-[200px] shadow-sm border">
        <div className="p-4">
          <h3 className="font-semibold text-sm">{strategy.name}</h3>
          <div className="text-gray-700 font-semibold flex justify-between gap-1 items-center">
            {strategy.symbol}
            <Image
              src={cryptoLogos[strategy.symbol]}
              alt={strategy.symbol}
              width={16}
              height={24}
              className="object-contain h-10"
            />
          </div>
          <p className="text-gray-500">{strategy.returns}%</p>
          <p className="text-gray-500">Minimum: {strategy.minimumAmount} {strategy.symbol}</p>
        </div>
      </div>
    ))
  }

  const renderText = (text: any) => {
    return <div>{text}</div>
  }
  return (
    <div className="max-w-4xl w-full mx-auto flex flex-col h-[calc(100vh-140px)]">
      {/* Chat Header */}
      <div className="border-b flex items-center justify-between p-3">
      <div className="text-muted-foreground text-sm">
          System: AI Quant powered by tailored cutting-edge models
          <br />
          Status: Ready for input
        </div>
      </div>

      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-4">


        {/* Messages */}
        {messages.map((message, index) => (
          <div key={index} className="whitespace-pre-wrap">
            {message.role === "user" ? "> " : ""}
            {message.type === "text" ? renderText(message.content) :
              <div className="flex overflow-x-auto space-x-4 p-2">
                {renderStrategies(message.content as any[])}
              </div>

            }
          </div>
        ))}

        {/* Typing Effect Message */}
        {
          isLoading ? (
            <div className="whitespace-pre-wrap">
              <Image
                src="/sentient.png"
                alt="Typing..."
                width={20}
                height={20}
                className="animate-spin animate-infinite animate-ease-in-out"
                />
            </div>
          ) :
          currentTypingMessage && (
            <div className="whitespace-pre-wrap">{currentTypingMessage}</div>
          )
        }
        {error && <div className="text-destructive">Error: {error}</div>}
        {/* Scroll to bottom anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Section - Fixed at Bottom */}
      <div className="p- bg-white sticky bottom-0">
        <form onSubmit={handleSubmit} className="relative">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter command..."
            className="pr-10"
            disabled={isLoading || currentTypingMessage !== null}
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 disabled:opacity-50"
            disabled={isLoading || currentTypingMessage !== null || !input.trim()}
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  )
}