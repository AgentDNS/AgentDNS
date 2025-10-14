#!/usr/bin/env python3
"""
Helper script to generate ENCRYPTION_KEY
"""

from cryptography.fernet import Fernet

def generate_encryption_key():
    """Generate a new encryption key"""
    key = Fernet.generate_key()
    return key.decode()

if __name__ == "__main__":
    encryption_key = generate_encryption_key()
    print("=== AgentDNS Encryption Key Generator ===")
    print(f"ENCRYPTION_KEY: {encryption_key}")
    print()
    print("Please add the above key to your .env file:")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print()
    print("⚠️  Important:")
    print("1. Store this key securely; without it, stored data cannot be decrypted")
    print("2. Do not hardcode this key in source code")
    print("3. In production, use a secure secret management service")