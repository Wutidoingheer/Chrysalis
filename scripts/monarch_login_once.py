import asyncio
from monarchmoney import MonarchMoney

async def main():
    mm = MonarchMoney()
    await mm.interactive_login()   # Prompts for email, password, and handles OTP/MFA
    mm.save_session()
    print("✅ Saved Monarch session.")

if __name__ == "__main__":
    asyncio.run(main())
