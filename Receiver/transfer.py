import time
import threading
import sys
import msvcrt  
from mnemonic import Mnemonic
from web3 import Web3
from eth_account import Account
from tqdm import tqdm  
from dotenv import load_dotenv
import os

load_dotenv()

seed_phrase = os.getenv("SEED_PHRASE")
infura_url = os.getenv("INFURA_URL")
target_wallet = os.getenv("TARGET_WALLET")

Account.enable_unaudited_hdwallet_features()

mnemo = Mnemonic("english")

seed = mnemo.to_seed(seed_phrase)

def derive_private_key(seed_phrase, index):
    return Account.from_mnemonic(seed_phrase, account_path=f"m/44'/60'/0'/0/{index}").key

web3 = Web3(Web3.HTTPProvider(infura_url))

if web3.is_connected():
    print("Connected to the network")
else:
    print("Connection failed")
    sys.exit()

# Number of wallets to include for the transfer
number_of_wallets = 11 

wallets = []
print("Deriving wallets from seed phrase...")
for i in range(number_of_wallets):
    private_key = derive_private_key(seed_phrase, i)
    address = Account.from_key(private_key).address
    wallets.append({"address": address, "private_key": private_key.hex()})

# Include if you want to have a list of wallets and their individual balances
print("\nAnalyzing wallets:")
total_eth = 0
for i, wallet in enumerate(wallets):
    from_address = wallet["address"]
    balance = web3.eth.get_balance(from_address)
    wallets[i]['balance'] = balance
    total_eth += balance
    print(f"Wallet {i+1}: Address = {from_address}, Balance = {web3.from_wei(balance, 'ether')} ETH")

print(f"\nTotal wallets: {number_of_wallets}")
print(f"Total ETH across all wallets: {web3.from_wei(total_eth, 'ether')} ETH")

print(f"\nTarget wallet address: {target_wallet}")

confirmation = input("\nDo you want to proceed with transferring the balances to the target wallet? (yes/no): ").strip().lower()
if confirmation != 'yes':
    print("Transfer cancelled.")
    sys.exit()

def send_eth(from_address, from_private_key, to_address, amount_wei):
    nonce = web3.eth.get_transaction_count(from_address)
    gas_price = web3.eth.gas_price
    gas_limit = 21000  

    tx = {
        'nonce': nonce,
        'to': to_address,
        'value': amount_wei,
        'gas': gas_limit,
        'gasPrice': gas_price
    }

    signed_tx = web3.eth.account.sign_transaction(tx, from_private_key)

    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()

def listen_for_keypress():
    global stop_flag
    print("Press any key to stop the script...")
    msvcrt.getch()  # Wait for a key press
    stop_flag = True

def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"Waiting {i} seconds before the next transaction...", end="\r")
        time.sleep(1)
    print(" " * 50, end="\r")  

stop_flag = False

keypress_thread = threading.Thread(target=listen_for_keypress)
keypress_thread.start()

with tqdm(total=number_of_wallets, desc="Transferring wallets") as pbar:
    for i, wallet in enumerate(wallets):
        if stop_flag:
            print("\nScript stopped by user.")
            break

        from_address = wallet["address"]
        from_private_key = wallet["private_key"]

        balance = wallet["balance"]
        if balance > 0:
            gas_price = web3.eth.gas_price
            gas_limit = 21000
            gas_fee = gas_price * gas_limit
            amount_to_send = balance - gas_fee

            if amount_to_send > 0:
                try:
                    print(f"\nTransferring {web3.from_wei(amount_to_send, 'ether')} ETH from {from_address} to {target_wallet} ({i+1}/{number_of_wallets})")
                    tx_hash = send_eth(from_address, from_private_key, target_wallet, amount_to_send)
                    print(f"Transaction sent: {tx_hash}")
                    # Internals between each transaction
                    countdown(5)
                except ValueError as e:
                    print(f"\nError sending transaction from wallet {from_address}: {e}")
            else:
                print(f"\nNot enough balance to cover the gas fees for wallet: {from_address}")
        else:
            print(f"\nNo balance to transfer for wallet: {from_address}")

        pbar.update(1)

print("\nAll transfers complete.")