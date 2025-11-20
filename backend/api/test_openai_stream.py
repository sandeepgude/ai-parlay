# import asyncio
# from openai import AsyncOpenAI


# client = AsyncOpenAI(api_key ="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")


# async def main():
#     print("Connecting to OpenAI...")
#     try:
#         async with client.chat.completions.stream(
#             model="gpt-4o",
#             messages=[{"role": "user", "content": "Say hello"}],
#         ) as stream:
#             async for event in stream:
#                 if event.type == "message.delta" and event.delta.content:
#                     print(event.delta.content, end="", flush=True)
#             print("\n✅ Stream completed.")
#     except Exception as e:
#         print("❌ ERROR:", e)

# asyncio.run(main())
