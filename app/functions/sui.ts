import { Ed25519Keypair } from '@mysten/sui/keypairs/ed25519';

export const createSuiWallet = async () => {
    const keypair = Ed25519Keypair.generate();
    const publicKey = keypair.getPublicKey().toSuiAddress();
    const secretKey = keypair.getSecretKey();
    const obj = {
        publicKey,
        secretKey
    }
    console.log(obj)
    return obj
}   