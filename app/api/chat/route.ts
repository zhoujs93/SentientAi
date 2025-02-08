/* eslint-disable @typescript-eslint/no-explicit-any */
import OpenAI from "openai"
import { NextResponse } from "next/server"
import {
  quantPrompt,
  tools,
} from "@/app/ai/ai"
import Strategies from "@/app/functions/strategies"
const openai = new OpenAI({
  baseURL: "https://api.atoma.network/v1",
  apiKey: process.env.ATOMA_API_KEY,
  // apiKey: process.env.OPENAI_API_KEY,
})


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
      role: "developer",
      content: quantPrompt,
    }, ...messages]
    console.log('msgs', msgs)
    const completion = await openai.chat.completions.create({
      model: "meta-llama/Llama-3.3-70B-Instruct", // Changed from gpt-4o to gpt-4
      // model: "gpt-4o-mini",
      messages: msgs,
      tool_choice: "auto", 
      tools: tools.map(tool => ({ ...tool, type: "function" })),
      temperature: 1.5,
    })

    let content: string | any = completion.choices[0]?.message?.content || ""
    console.log(JSON.stringify(content, null, 2))
    if (typeof content === "string") {
      content = content.replace("<|eom_id|>", "").trim();
    }
    let isFunctionCall = false
    let type = "text"
    if (content.startsWith("{")) {
      try {
        content = JSON.parse(content) as { type: string; function: object }
        if (content.type === "function") {
          isFunctionCall = true
        }
      } catch (error) {
        console.error("Failed to parse JSON response from OpenAI:", error)
      }
    }
    if (isFunctionCall) {
      const { name } = content.function
      switch (name) {
        case "getAvailableStrategies":
          const strats = Strategies.getAvailableStrategies()
          content = strats
          type = "strategies"
          break
        case "startStrategy":
          const { strategyId, amount, currency, riskLevel } = content.function.parameters
          content = Strategies.startStrategy({ strategyId, amount:  Number(amount), currency, riskLevel })
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

