/* eslint-disable @typescript-eslint/no-explicit-any */
import axios from "axios";

class Strategies {

    async startStrategy({
        strategyId,
        amount,
        takeProfitThreshold,
        stopLossThreshold,
        walletPrivateKey,
        walletPublicKey,
        walletSecretKey
    }:{
        strategyId: string;
        amount: any;
        takeProfitThreshold: any;
        stopLossThreshold: any;
        walletPrivateKey: any;
        walletPublicKey: any;
        walletSecretKey: any;
    }) {
        // Start the strategy
        try {
            const reqBody = {
                privateKey: walletPrivateKey,
                secretKey: walletSecretKey,
                publicKey: walletPublicKey,
                quoteSymbolQuantity: amount,
                take_profit: takeProfitThreshold,
                stop_loss: stopLossThreshold,
            }
            console.log("Request body:", reqBody, strategyId);
            const startStrat = await axios.post("http://34.130.61.46:9001/run-strategy", reqBody);
            return {
                message: startStrat.data.message,
                // privateKey: walletPrivateKey,
                privateKey: 'suiprivkey1qpegeh79fxexr0lunpzcdnepz4gqp5344kw54lemn0jn28c7spxjg7w0xjs',
                publicKey: walletPublicKey,
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
        const strategy1 = {
            name: `Strategy 1 for ETH`,
            symbol: cryptocurrencies[1],
            minimumAmount: 0.01,
            description: "Strategy 1 is a customized short term quantitative trading strategy where the signal is generated from a machine learning model designed to trade ETH futures. As for the results, from our out of sample back-tests, the historical returns generated for this model was around 50% from October 2024 - January 2025.",
            returns: 50
        };
        strategies.push(strategy1);
        return strategies;
    }
}

export default new Strategies();