/* eslint-disable @typescript-eslint/no-explicit-any */

import { NextResponse } from "next/server"
import {
  quantPrompt,
  tools,
} from "@/app/ai/ai"
import Strategies from "@/app/functions/strategies"
import { startCompletion } from "@/app/ai/chat"
// import strategies from "@/app/functions/strategies"
import { createSuiWallet } from "@/app/functions/sui"


export async function POST(req: Request) {
  if (!process.env.OPENAI_API_KEY) {
    return NextResponse.json({ error: "OpenAI API key is not configured" }, { status: 500 })
  }

  try {
    let { messages } = await req.json()
    messages = messages.map((message: any) => {
      console.log('message', message)
      return {
        role: message.role,
        content: JSON.stringify(message.content),
      }
    })
    if (!Array.isArray(messages)) {
      return NextResponse.json({ error: "Invalid messages format" }, { status: 400 })
    }
    const msgs = [{
      role: "system",
      content: quantPrompt,
    }, ...messages]
    console.log('msgs', msgs)
    const completion = await startCompletion({ messages: msgs, tools })

    let content: string | any = completion.choices[0]?.message?.content || ""
    const tool_call: any = completion.choices[0]?.message?.tool_calls?.[0]
    const message: any = completion.choices[0]?.message
    console.log(JSON.stringify(completion, null, 2))
    
    let isFunctionCall = false
    let type = "text"
    if (content.includes("<|python_tag|>")) {
      content = content.replace("<|python_tag|>", "").trim()
      isFunctionCall = true
    }
    if (content.includes("<|eom_id|>")){
      content = content.replace("<|eom_id|>", "").trim()
      content = JSON.parse(content)
      console.log('content', content)
      isFunctionCall = true
    } else if (content.startsWith("{")) {
      try {
        content = JSON.parse(content) as { type: string; function: object }
        if (content.type === "function") {
          isFunctionCall = true
        }
      } catch (error) {
        console.error("Failed to parse JSON response from OpenAI:", error)
      }
    } else if (tool_call) {
      isFunctionCall = true
      content = tool_call
    }
    if (isFunctionCall) {
      const { name } = content.function || content
      const tool_call_id = content.id || false
      const msgObj: any = {
        role: "tool",
        tool_call_id: tool_call_id,
        name: name,
      }
      if (tool_call_id) {
        msgObj.tool_call_id = tool_call_id || "abcd123"
      }
      switch (name) {
        case "getAvailableStrategies":
          const strats = Strategies.getAvailableStrategies()
          content = strats

          // const toolCallMsg = {
          //   role: "assistant",
          //   tool_calls: [
          //     {
          //       "type": "function",
          //       "id": "abcd123",
          //       "function": {
          //         "name": "getAvailableStrategies",
          //         "arguments": {},
          //       }
          //     }
          //   ],
          //   content: ''
          // }
          msgObj.content = JSON.stringify(strats, null, 2)

          content: JSON.stringify(strats, null, 2)
          const newMsgs = [...msgs, message, msgObj]
          console.log('newMsgs', newMsgs)
          const newCompletion = await startCompletion({ messages: newMsgs, tools })
          content = newCompletion.choices[0]?.message?.content || ""
          console.log('newCompletion', JSON.stringify(newCompletion, null, 2))
          break
        case "startStrategy":
          const { strategyId, amount, takeProfitThreshold, stopLossThreshold } = content.function.arguments
          const { message: outputmsg, privateKey, publicKey} = await Strategies.startStrategy({ strategyId, amount:  Number(amount), takeProfitThreshold, stopLossThreshold })
          msgObj.content = JSON.stringify({ outputmsg, privateKey, publicKey }, null, 2)
          const newMsgs2 = [...msgs, message, msgObj]
          console.log('newMsgs2', newMsgs2)
          const newCompletion2 = await startCompletion({ messages: newMsgs2, tools })
          content = newCompletion2.choices[0]?.message?.content || ""
          console.log('newCompletion2', JSON.stringify(newCompletion2, null, 2))  
          type = "text"
          break
        case "createWallet":
          content = await createSuiWallet()
          
          type = "text"
          break
        case "stopStrategy":
          // check if user has any active strategies
          content = "Ended strategy"
          type = "text"
          break
        default:
          throw new Error(`Unknown function "${name}"`)
      }
    } else if (typeof content !== "string") {
      throw new Error("Invalid response from OpenAI")
    }

    return NextResponse.json({ 
      type,
      content
    })
  } catch (error) {
    console.error("OpenAI API error:", error)
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred"
    return NextResponse.json({ error: errorMessage }, { status: 500 })
  }
}

