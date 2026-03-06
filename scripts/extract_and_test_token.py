"""
Interactive script to help extract and test a Monarch Money session token.

This script will:
1. Guide you through extracting the token
2. Let you paste it in
3. Test if it works
4. Save it for future use
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from monarchmoney import MonarchMoney

def print_instructions():
    print("\n" + "="*60)
    print("MONARCH MONEY TOKEN EXTRACTION HELPER")
    print("="*60)
    print("\n📋 STEP-BY-STEP INSTRUCTIONS:")
    print("\n1. Open https://app.monarchmoney.com in your browser")
    print("2. Make sure you're logged in")
    print("3. Press F12 to open Developer Tools")
    print("4. Click on the 'Network' tab")
    print("5. Refresh the page (F5) or navigate to trigger requests")
    print("6. Look for a request to 'api.monarchmoney.com/graphql'")
    print("7. Click on that request")
    print("8. In the 'Request Headers' section, find 'Authorization'")
    print("9. Copy the token value (the part after 'Token ' or 'Bearer ')")
    print("\n" + "-"*60)
    print("The Authorization header will look like:")
    print("  Authorization: Token abc123xyz789...")
    print("  OR")
    print("  Authorization: Bearer abc123xyz789...")
    print("\nCopy ONLY the token part (abc123xyz789...), not 'Token' or 'Bearer'")
    print("-"*60 + "\n")

async def test_token(token: str):
    """Test if a token works by trying to fetch accounts."""
    print(f"\n🔍 Testing token: {token[:20]}..." if len(token) > 20 else f"\n🔍 Testing token...")
    
    # Create MonarchMoney instance with token
    mm = MonarchMoney(token=token)
    
    # Manually set the authorization header to ensure it's correct
    mm._headers["Authorization"] = f"Token {token}"
    
    try:
        # Try to fetch accounts using the account service directly
        # This bypasses some of the GraphQL client initialization issues
        accounts = await mm.get_accounts()
        
        # Handle both dict and list responses
        if isinstance(accounts, dict):
            account_list = accounts.get("results", accounts.get("accounts", []))
        else:
            account_list = accounts
        
        print(f"✅ SUCCESS! Token is valid!")
        print(f"   Found {len(account_list)} accounts")
        
        # Show account names
        if account_list and len(account_list) > 0:
            print("\n   Account names:")
            for i, acc in enumerate(account_list[:5], 1):  # Show first 5
                name = acc.get("name", acc.get("displayName", "Unknown"))
                print(f"   {i}. {name}")
            if len(account_list) > 5:
                print(f"   ... and {len(account_list) - 5} more")
        
        return True, mm
        
    except Exception as e:
        print(f"❌ Token test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        # Try to get more details
        if hasattr(e, '__cause__') and e.__cause__:
            print(f"   Caused by: {e.__cause__}")
        return False, None

async def main():
    # Load existing .env if it exists
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        # Check for token in multiple possible variable names
        existing_token = os.getenv("MONARCH_AUTHORIZATION") or os.getenv("MONARCH_SESSION_TOKEN") or os.getenv("MONARCH_BEARER")
        if existing_token:
            # Handle "Token xxx" or "Bearer xxx" format
            if existing_token.startswith("Token ") or existing_token.startswith("Bearer "):
                existing_token = existing_token.split(" ", 1)[1]
            print(f"\n📝 Found existing token in .env file")
            use_existing = input("Do you want to test the existing token? (y/n): ").strip().lower()
            if use_existing == 'y':
                valid, mm = await test_token(existing_token)
                if valid:
                    mm.save_session()
                    print(f"\n✅ Session saved! You can now use regular scripts.")
                    return
    
    # Show instructions
    print_instructions()
    
    # Get token from user
    print("Paste your token here (or press Enter to skip):")
    token = input("Token: ").strip()
    
    if not token:
        print("\n⚠️  No token provided. Exiting.")
        print("\n💡 Tip: You can also add MONARCH_SESSION_TOKEN to your .env file")
        return
    
    # Test the token
    valid, mm = await test_token(token)
    
    if valid:
        # Ask if user wants to save it
        save = input("\n💾 Save this token to .env file? (y/n): ").strip().lower()
        
        if save == 'y':
            # Update .env file
            env_lines = []
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Remove existing token lines
            env_lines = [line for line in env_lines if not any(
                line.strip().startswith(f'{key}=') 
                for key in ['MONARCH_AUTHORIZATION', 'MONARCH_SESSION_TOKEN', 'MONARCH_BEARER']
            )]
            
            # Add new token (use MONARCH_AUTHORIZATION as primary)
            env_lines.append(f'\nMONARCH_AUTHORIZATION={token}\n')
            
            # Write back
            with open(env_path, 'w') as f:
                f.writelines(env_lines)
            
            print(f"✅ Token saved to {env_path}")
        
        # Save session file
        mm.save_session()
        print(f"✅ Session saved to: {mm._session_file}")
        print("\n🎉 You're all set! You can now use regular scripts without logging in.")
    else:
        print("\n❌ Token validation failed.")
        print("\n💡 Tips:")
        print("   - Make sure you copied the entire token (they can be very long)")
        print("   - Try extracting a fresh token from your browser")
        print("   - Make sure you're logged into Monarch Money in your browser")
        print("   - Check that there are no extra spaces in the token")

if __name__ == "__main__":
    asyncio.run(main())

