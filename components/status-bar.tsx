"use client"

import { useWallet } from "@suiet/wallet-kit"
import { Settings, Bell } from "lucide-react"
import Clock from "./ui/Clock"

export function StatusBar() {
  const { connected } = useWallet()

  return (
    <div className="h-8 border-t bg-background flex items-center px-4 text-sm">
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
          <span>Sui</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span>Solana</span>
        </div>
      </div>
      <div className="ml-auto flex items-center space-x-4">
        <Bell className="w-4 h-4" />
        <Settings className="w-4 h-4" />
        <Clock />
      </div>
    </div>
  )
}

