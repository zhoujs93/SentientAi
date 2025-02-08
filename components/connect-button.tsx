"use client"

import { ConnectButton as SuietConnectButton } from "@suiet/wallet-kit"
// import { Button } from "@/components/ui/button"

export function ConnectButton() {
  return (
    <SuietConnectButton>
      {/* {({ connected, connecting, connect, disconnect }) => (
        <Button
          onClick={connected ? disconnect : connect}
          variant={connected ? "outline" : "default"}
          size="sm"
          className="text-xs"
        >
          {connecting ? "Connecting..." : connected ? "Connected to Sui" : "Connect to Sui"}
        </Button>
      )} */}
    </SuietConnectButton>
  )
}

