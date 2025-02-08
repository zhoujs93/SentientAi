import { Ed25519Keypair } from '@mysten/sui/keypairs/ed25519';

export const createSuiWallet = async () => {
    const keypair = Ed25519Keypair.generate();
    const publicKey = keypair.getPublicKey();
    const privatekey = keypair.getSecretKey();
    return {
        publicKey,
        privatekey
    }
}   