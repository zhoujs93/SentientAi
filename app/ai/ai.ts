export const quantPrompt = `
    Your are an AI agent named SigmaChad. Your main task is to help users trade cryptocurrencies on the SUI platform using our custom strategies.
    Note that the users wallet state will be passed on to you as follows:
    -- If the user's wallet is connected, you will receive the wallet address like this: --wallet-address <wallet-address>. Do not use this flag to get the user's wallet balance.
    -- If the user's wallet is not connected, you will receive the following flag: --user-wallet-not-connected. Only use this flag to determine if the user's wallet is not connected.
    -- If the user's wallet is not connected, politely inform the user, do not create a wallet for the user.
    -- If the user's wallet is connected, do not prompt the user to connect their wallet or try to get their suiBalance.

    Your tasks are as follows:
    - Introduce yourself at the very beginning of a conversation. Do not introduce yourself more than once in a conversation.
    - Answer any questions the user has about trading that do not require you to create
    - The following list of tasks all require the users wallet to be connected to the SUI platform. If the user's wallet is not connected, you should prompt the user to connect their wallet.
    -- If the user asks you for a list of strategies, provide them with the available strategies using the appropriate function from the tools provided.
    -- If the user asks you for details about a specific strategy, provide them with the details of the strategy using the appropriate function from the tools provided.
    -- If the user asks you to start a strategy, start the strategy using the appropriate function from the tools provided.
    -- If the user asks you to stop a strategy, stop the strategy using the appropriate function from the tools provided.
    -- If the user asks you for the status of a strategy, provide them with the status of the strategy using the appropriate function from the tools provided.
    -- Always end the conversation politely.

    Only use the tools provided to complete the tasks if and only if the user has asked you to.

    Do not do the following:
    -- Call any functions unless the user has asked you to.
    -- Ask the user for any personal information.
    -- Do not get the users wallet balance unless the user has asked you to.

    If a tool call is required, use the following format as pure json and pure json only:
    { 
        "type": "function",
        "function": {
            "name": "functionName",
            "parameters": {
                "parameter1": "value1",
                "parameter2": "value2"
            }
        }
    }
`;
export const tools = [
    {
      type: "function",
      function: {
        name: "createSuiWallet",
        description: "Creates a new SUI wallet for the user",
        parameters: {
          type: "object",
          properties: {
            walletAddress: {
              type: "string",
              description: "The wallet address of the user"
            }
          },
          required: ["walletAddress"]
        }
      }
    },
    // {
    //   type: "function",
    //   function: {
    //     name: "getSuiWallet",
    //     description: "Retrieves the SUI wallet of the user",
    //     parameters: {
    //       type: "object",
    //       properties: {
    //         walletAddress: {
    //           type: "string",
    //           description: "The wallet address of the user"
    //         }
    //       },
    //       required: ["walletAddress"]
    //     }
    //   }
    // },
    {
      type: "function",
      function: {
        name: "getSuiBalance",
        description: "Retrieves the SUI balance of the user",
        parameters: {
          type: "object",
          properties: {
            walletAddress: {
              type: "string",
              description: "The wallet address of the user"
            }
          },
          required: ["walletAddress"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "getAvailableStrategies",
        description: "Retrieves the available strategies for trading",
        parameters: {
          type: "object",
          properties: {}
        }
      }
    },
    {
      type: "function",
      function: {
        name: "getStrategy",
        description: "Retrieves the details of a strategy",
        parameters: {
          type: "object",
          properties: {
            strategyId: {
              type: "string",
              description: "The ID of the strategy"
            }
          },
          required: ["strategyId"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "startStrategy",
        description: "Starts a strategy for trading",
        parameters: {
          type: "object",
          properties: {
            strategyId: {
              type: "string",
              description: "The ID of the strategy"
            },
            amount: {
              type: "number",
              description: "The amount to trade"
            },
            currency: {
              type: "string",
              description: "The cryptocurrency to trade"
            },
            riskLevel: {
              type: "number",
              description: "The risk level of the trade"
            }
          },
          required: ["strategyId", "amount", "currency", "riskLevel"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "stopStrategy",
        description: "Stops a strategy for trading",
        parameters: {
          type: "object",
          properties: {
            strategyId: {
              type: "string",
              description: "The ID of the strategy"
            }
          },
          required: ["strategyId"]
        }
      }
    },
    {
      type: "function",
      function: {
        name: "getStrategyStatus",
        description: "Retrieves the status of a strategy",
        parameters: {
          type: "object",
          properties: {
            strategyId: {
              type: "string",
              description: "The ID of the strategy"
            }
          },
          required: ["strategyId"]
        }
      }
    }
  ];
