import sys

from eth_account import Account
from eth_keys.datatypes import PrivateKey

print("Paste in 12 word mnemonic then press Ctrl-D twice\n")

mnemonic_txt = sys.stdin.read()

print("\n")

mnemonic = mnemonic_txt.split()


Account.enable_unaudited_hdwallet_features()
# pylint: disable=no-value-for-parameter
acct = Account.from_mnemonic(" ".join(mnemonic))

print(f"\n\nAddress: {acct.address}")

compressed_bytes = PrivateKey(acct.key).public_key.to_compressed_bytes()
print(f"Compressed bytes address (Starling Capture): {compressed_bytes.hex()}")
