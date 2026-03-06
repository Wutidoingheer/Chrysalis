"""
Script to use a manually extracted session token from browser.

This is useful when the login endpoints are not working.
Extract the token from your browser (see get_session_from_browser.md) and use it here.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from monarchmoney import MonarchMoney

async def main():
    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # Get token from environment variable (support multiple names)
    auth_header = os.getenv("MONARCH_AUTHORIZATION") or os.getenv("MONARCH_SESSION_TOKEN") or os.getenv("MONARCH_BEARER")
    
    if not auth_header:
        print("❌ Error: No token found in .env")
        print("\nTo use this script, add one of these to your .env file:")
        print("   MONARCH_AUTHORIZATION=your_token_here")
        print("   OR")
        print("   MONARCH_SESSION_TOKEN=your_token_here")
        print("   OR")
        print("   MONARCH_BEARER=your_token_here")
        print("\n(Extract token from browser - see get_session_from_browser.md)")
        return
    
    # Handle "Token xxx" or "Bearer xxx" format, or just the token
    if auth_header.startswith("Token "):
        token = auth_header.split(" ", 1)[1]  # Extract just the token part
    elif auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]  # Extract just the token part
    else:
        token = auth_header  # Assume it's just the token
    
    print(f"Using provided session token: {token[:20]}..." if len(token) > 20 else "Using provided session token...")
    mm = MonarchMoney(token=token)
    
    # Ensure the Authorization header is set correctly
    mm._headers["Authorization"] = f"Token {token}"
    mm._token = token
    
    # Debug: Show what headers we're sending
    print(f"\n📋 Request headers being sent:")
    print(f"   Authorization: {mm._headers.get('Authorization', 'Not set')[:50]}...")
    print(f"   Device-Uuid: {mm._headers.get('Device-Uuid', mm._headers.get('device-uuid', 'Not set'))}")
    print(f"   Origin: {mm._headers.get('Origin', 'Not set')}")
    print(f"   Monarch-Client: {mm._headers.get('Monarch-Client', 'Not set')}")
    print(f"   Monarch-Client-Version: {mm._headers.get('Monarch-Client-Version', 'Not set')}")
    from monarchmoney.monarchmoney import MonarchMoneyEndpoints
    print(f"   GraphQL URL: {MonarchMoneyEndpoints.getGraphQL()}")
    
    # Test the session by fetching accounts
    try:
        print("\nTesting session by fetching accounts...")
        accounts = await mm.get_accounts()
        
        # Handle both dict and list responses
        if isinstance(accounts, dict):
            account_list = accounts.get("results", accounts.get("accounts", []))
        else:
            account_list = accounts
        
        print(f"✅ Session is valid! Found {len(account_list)} accounts")
        
        # Save the session for future use
        mm.save_session()
        print(f"✅ Session saved to: {mm._session_file}")
        print("\nYou can now use the regular scripts without needing to login again!")
        
    except Exception as e:
        print(f"❌ Session test failed: {e}")
        print("\nThe token might be expired or invalid.")
        print("Please extract a fresh token from your browser.")

if __name__ == "__main__":
    asyncio.run(main())

