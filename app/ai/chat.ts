/* eslint-disable @typescript-eslint/no-explicit-any */
import OpenAI from "openai"
// const openai = new OpenAI({
//     baseURL: "https://api.atoma.network/v1",
//     apiKey: process.env.ATOMA_API_KEY,
//     // apiKey: process.env.OPENAI_API_KEY,
// })



interface StartCompletionProps {
    messages: any
    tools: any
}
const startCompletion: (props: StartCompletionProps) => Promise<any> = async ({ messages, tools = []}) => {
    try {
        const openai = new OpenAI({
            // baseURL: "https://api.atoma.network/v1",
            // apiKey: process.env.ATOMA_API_KEY,
            apiKey: process.env.OPENAI_API_KEY,
        })
    const obj: any = {
        // model: "meta-llama/Llama-3.3-70B-Instruct", // Changed from gpt-4o to gpt-4
        model: "gpt-4o-mini",
        messages: messages,
        tool_choice: "auto", 
        tools: tools.map((tool: any) => ({ ...tool, type: "function" })),
        // tools: [tools[0]],
        // functions: tools.map(tool => tool.function),
        temperature: 0.0,
    }
        
    console.log('---------------------------------------------------------------------')
    console.log(obj)
    console.log('---------------------------------------------------------------------')
    const completion = await openai.chat.completions.create(obj)

    return completion
} catch (error) {
    console.error("Failed to start completion:", error)
    throw error
}
}

export { startCompletion }