/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"

import { useWallet } from "@suiet/wallet-kit"
import { Settings, Bell } from "lucide-react"
import dynamic from "next/dynamic"
import { useEffect, useState } from "react"
import {getWalletBalance} from "@/app/sui/client"
import Image from "next/image"
const Clock = dynamic(() => import("@/components/ui/Clock"), { ssr: false })

export function StatusBar() {
  const wallet = useWallet()
  const { connected } = wallet
  const [usdcBalance, setUsdcBalance] = useState<number>(0)


  const getUSDCBalance = async () => {
    const balance = await getWalletBalance(wallet.address as string)
    setUsdcBalance(balance)
  }
  useEffect(() => {
    if (wallet && wallet.connected) getUSDCBalance()
  },[wallet.connected])


  return (
    <div className="h-8 border-t bg-background flex items-center px-4 text-sm">
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
          <span>Sui</span>
        </div>
        {
          connected && (
            <div className="flex items-center space-x-1.5">
              <Image
                src="https://cryptologos.cc/logos/usd-coin-usdc-logo.png"
                alt="USDC"
                width={16}
                height={16}
              />
              <span>{usdcBalance.toFixed(2)} USDC</span>
            </div>
          )
        }
      </div>
      <div className="ml-auto flex items-center space-x-4">
        <Bell className="w-4 h-4" />
        <Settings className="w-4 h-4" />
        <Clock />
      </div>
    </div>
  )
}

