/* eslint-disable @typescript-eslint/no-explicit-any */
import { getFullnodeUrl, SuiClient } from '@mysten/sui/client';
const USDCAddress: string = "0xa1ec7fc00a6f40db9693ad1415d0c193ad3906494428cf252621037bd7117e29::usdc::USDC";
const USDCDecimals = 6


const rpcUrl: string = getFullnodeUrl('testnet');
const client = new SuiClient({ url: rpcUrl });


export const getWalletBalance = async (address: string) => {
    const balance = await client.getAllBalances({
      owner: address as string,
    })
    const USDCBal: any = balance.find((b)=> b.coinType === USDCAddress)
    let USDCAmount = 0
    if (USDCBal) {
        USDCAmount = (USDCBal.totalBalance / 10 ** USDCDecimals)
    }
    return USDCAmount
}


export default client;