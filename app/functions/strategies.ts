class Strategies {

    startStrategy({
        strategyId,
        amount,
        currency,
        riskLevel
    }:{
        strategyId: string;
        amount: number;
        currency: string;
        riskLevel: number;
    }) {
        // Start the strategy
        console.log(`Starting strategy ${strategyId} for ${amount} ${currency} with risk level ${riskLevel}`);
        return `Started strategy ${strategyId} for ${amount} ${currency} with risk level ${riskLevel}`;
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
        for (let i = 0; i < 10; i++) {
            const randomCrypto = Math.floor(Math.random() * cryptocurrencies.length);
            // minimum amount is a random number between 10 and 1000 and must be divisible by 10 and ends with 0
            const minimumAmount = Math.floor(Math.random() * 100) * 10 + 10;
            // returns are any single decimal number between 0 and 100
            const returns = Math.floor(Math.random() * 100) / 10;
            const strategy = {
                name: `Strategy ${i + 1} for ${cryptocurrencies[randomCrypto]}`,
                symbol: cryptocurrencies[i],
                minimumAmount,
                returns
            };
            strategies.push(strategy);
        }
        return strategies;
    }
}

export default new Strategies();