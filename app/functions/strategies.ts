import axios from "axios";
import { createSuiWallet } from "./sui";
class Strategies {

    async startStrategy({
        amount,
        takeProfitThreshold,
        stopLossThreshold,
    }:{
        strategyId: string;
        amount: number;
        takeProfitThreshold: number;
        stopLossThreshold: number;
    }) {
        // Start the strategy
        try {
            const suiWallet = await createSuiWallet();
            console.log("SUI Wallet:", suiWallet);
            const privateKey = suiWallet.privatekey
            const startStrat = await axios.post("http://34.69.234.196:9001/run-strategy", {
                privateKey,
                quoteSymbolQuantity: amount,
                take_profit: takeProfitThreshold,
                stop_loss: stopLossThreshold,
            });
            return {
                message: startStrat.data.message,
                privateKey: suiWallet.privatekey,
                publicKey: suiWallet.publicKey,
            }
        } catch (error) {
            console.error("Failed to start strategy:", error);
            throw error;
        }
    }
    getAvailableStrategies() {
        const cryptocurrencies = [
            "BTC",
            "ETH",
            "ADA",
            "SOL",
            "DOT",
            "DOGE",
            "LUNA",
            "AVAX",
            "UNI",
            "LINK",
            "SUI"
        ];
        const strategies = [];
        // for (let i = 0; i < 10; i++) {
        //     const randomCrypto = Math.floor(Math.random() * cryptocurrencies.length);
        //     // minimum amount is a random number between 10 and 1000 and must be divisible by 10 and ends with 0
        //     const minimumAmount = Math.floor(Math.random() * 100) * 10 + 10;
        //     // returns are any single decimal number between 0 and 100
        //     const returns = Math.floor(Math.random() * 100) / 10;
        //     const strategy = {
        //         name: `Strategy ${i + 1} for ${cryptocurrencies[randomCrypto]}`,
        //         symbol: cryptocurrencies[i],
        //         minimumAmount,
        //         returns
        //     };
        //     strategies.push(strategy);
        // }
        const strategy1 = {
            name: `Strategy 1 for ETH`,
            symbol: cryptocurrencies[1],
            minimumAmount: 2,
            returns: 1.5
        };
        strategies.push(strategy1);
        return strategies;
    }
}

export default new Strategies();