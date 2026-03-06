"""
Alternative login script that uses environment variables instead of interactive input.
This avoids issues with terminal input handling.

Usage:
1. Create a .env file in the financeApi directory with:
   MONARCH_EMAIL=your@email.com
   MONARCH_PASSWORD=yourpassword
   
2. Or set environment variables:
   $env:MONARCH_EMAIL="your@email.com"
   $env:MONARCH_PASSWORD="yourpassword"
   
3. Run: python scripts/monarch_login_env.py
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from monarchmoney import MonarchMoney, MFARequiredError

async def main():
    # Load environment variables from .env file if it exists
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    email = os.getenv("MONARCH_EMAIL")
    password = os.getenv("MONARCH_PASSWORD")
    mfa_secret_key = os.getenv("MONARCH_MFA_SECRET_KEY")  # Optional
    
    if not email or not password:
        print("❌ Error: MONARCH_EMAIL and MONARCH_PASSWORD must be set")
        print("\nOptions:")
        print("1. Create a .env file with:")
        print("   MONARCH_EMAIL=your@email.com")
        print("   MONARCH_PASSWORD=yourpassword")
        print("\n2. Or set environment variables:")
        print('   $env:MONARCH_EMAIL="your@email.com"')
        print('   $env:MONARCH_PASSWORD="yourpassword"')
        return
    
    print(f"Logging in as {email}...")
    mm = MonarchMoney()
    
    try:
        await mm.login(
            email=email,
            password=password,
            use_saved_session=True,  # Try saved session first
            save_session=True,
            mfa_secret_key=mfa_secret_key
        )
        print("✅ Login successful!")
        mm.save_session()
        print("✅ Session saved to:", mm._session_file)
    except MFARequiredError:
        print("⚠️  MFA required. Please provide MFA code:")
        mfa_code = input("MFA Code: ")
        await mm.multi_factor_authenticate(email, password, mfa_code)
        print("✅ MFA authentication successful!")
        mm.save_session()
        print("✅ Session saved to:", mm._session_file)
    except Exception as e:
        print(f"❌ Login failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

