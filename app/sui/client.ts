import { getFullnodeUrl, SuiClient } from '@mysten/sui/client';


const rpcUrl: string = getFullnodeUrl('testnet');
const client = new SuiClient({ url: rpcUrl });

export default client;