import time
import threading
import sys
import msvcrt  
from web3 import Web3
from eth_account import Account
from tqdm import tqdm  
from dotenv import load_dotenv
import os


load_dotenv()

private_key = os.getenv("PRIVATE_KEY")
infura_url = os.getenv("INFURA_URL")
target_wallets = os.getenv("TARGET_WALLETS").split(',')
eth_amount = float(os.getenv("ETH_AMOUNT"))

web3 = Web3(Web3.HTTPProvider(infura_url))

if web3.is_connected():
    print("Connected to Ethereum network")
else:
    print("Connection failed")
    sys.exit()

source_address = Account.from_key(private_key).address

print(f"Source wallet address: {source_address}")

source_balance = web3.eth.get_balance(source_address)
print(f"Source wallet balance: {web3.from_wei(source_balance, 'ether')} ETH")

def send_eth(from_address, from_private_key, to_address, amount_wei, nonce, gas_price):
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
    msvcrt.getch() 
    stop_flag = True

def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"Waiting {i} seconds before the next transaction...", end="\r")
        time.sleep(1)
    print(" " * 50, end="\r") 

stop_flag = False

print(f"Target wallets: {target_wallets}")
total_eth = eth_amount * len(target_wallets)
print(f"Total ETH to be transferred: {total_eth} ETH")

total_amount_needed = web3.to_wei(total_eth, 'ether') + 21000 * len(target_wallets) * web3.eth.gas_price
if source_balance < total_amount_needed:
    print("Error: Insufficient balance to cover the transfers and gas fees.")
    sys.exit()

confirmation = input("\nDo you want to proceed with transferring the balances to the target wallets? (yes/no): ").strip().lower()
if confirmation != 'yes':
    print("Transfer cancelled.")
    sys.exit()

keypress_thread = threading.Thread(target=listen_for_keypress)
keypress_thread.start()

amount_wei = web3.to_wei(eth_amount, 'ether')
nonce = web3.eth.get_transaction_count(source_address)
gas_price = web3.eth.gas_price

with tqdm(total=len(target_wallets), desc="Transferring", ncols=70) as pbar:
    for i, target_wallet in enumerate(target_wallets):
        if stop_flag:
            print("\nScript stopped by user.")
            break

        try:
            print(f"\nTransferring {eth_amount} ETH from {source_address} to {target_wallet} ({i+1}/{len(target_wallets)})")
            tx_hash = send_eth(source_address, private_key, target_wallet, amount_wei, nonce, gas_price)
            print(f"Transaction sent: {tx_hash}")
            print(f"Transaction link: https://etherscan.io/tx/{tx_hash}")

            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                print(f"Transaction {tx_hash} was successful.")
            else:
                print(f"Transaction {tx_hash} failed.")
            
            nonce += 1 
            countdown(10)  
        except ValueError as e:
            error_message = e.args[0]
            if 'nonce too low' in error_message:
                print(f"\nError sending transaction to wallet {target_wallet}: Nonce too low. Retrying with higher nonce.")
                nonce = web3.eth.get_transaction_count(source_address) + 1
                tx_hash = send_eth(source_address, private_key, target_wallet, amount_wei, nonce, gas_price)
                print(f"Transaction sent: {tx_hash}")
                print(f"Transaction link: https://etherscan.io/tx/{tx_hash}")
            elif 'replacement transaction underpriced' in error_message:
                print(f"\nError sending transaction to wallet {target_wallet}: Replacement transaction underpriced. Retrying with higher gas price.")
                gas_price = int(gas_price * 1.1)
                tx_hash = send_eth(source_address, private_key, target_wallet, amount_wei, nonce, gas_price)
                print(f"Transaction sent: {tx_hash}")
                print(f"Transaction link: https://etherscan.io/tx/{tx_hash}")
            else:
                print(f"\nError sending transaction to wallet {target_wallet}: {e}")

        pbar.update(1)

print("\nAll transfers complete.")