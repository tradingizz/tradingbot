import os
import yfinance as yf
import nest_asyncio
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

nest_asyncio.apply()

# 🔐 Setup your API keys (store these as env variables in Render)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
WEBHOOK_URL = "https://tradingbot2-onm4.onrender.com"
FUNDAMENTAL_PROMPT = """
Perform a detailed fundamental analysis of {stock_name} listed on {exchange} using the following real-time financial data:
{stock_data}


prompt 1:
Perform a detailed fundamental analysis of {stock_name} listed on [Stock Exchange] using the latest available financial data, valuation metrics, and key insights.
Your analysis should cover the following aspects:
1️⃣ Financial Statements Analysis
✅ Revenue Growth – Year-over-Year (YoY) and Quarter-over-Quarter (QoQ) changes
 ✅ Profitability Metrics – Gross margin, net margin, and operating margin
 ✅ Earnings Per Share (EPS) – Trends and future projections
 ✅ Debt Levels – Debt-to-equity ratio, interest coverage
 ✅ Cash Flow Analysis – Trends in operating cash flow and free cash flow
2️⃣ Valuation Metrics
📈 Price-to-Earnings (P/E) Ratio – Compared to industry peers
 📈 Price-to-Book (P/B) Ratio
 📈 Enterprise Value-to-EBITDA (EV/EBITDA)
 📈 Dividend Yield (If applicable)
3️⃣ Growth Potential & Competitive Positioning
🚀 Industry Trends – Growth prospects for the sector
 🏆 Competitive Advantage – Does the company have a strong market position?
 💡 Innovation & R&D – Is the company investing in future growth?
 👨‍💼 Management & Leadership – CEO track record, key executives
4️⃣ Risk Analysis
⚠️ Market Risks – Macroeconomic factors, geopolitical risks
 ⚠️ Operational Risks – Supply chain issues, lawsuits, regulatory challenges
 ⚠️ Debt & Liquidity Risks – Is the company financially stable?
5️⃣ Recent News & Catalysts
📊 Latest Earnings Report – Did they beat or miss expectations?
 🤝 Mergers & Acquisitions – Recent deals or partnerships
 📜 Regulatory Changes – Any new laws affecting the company?
 📢 Major Product Launches – Potential impact on future revenue
6️⃣ Investment Outlook & Conclusion
📈 Bullish Case – Why the stock could go up
 📉 Bearish Case – Potential downside risks
 📅 Short-term vs. Long-term Perspective – Investment horizon analysis
prompt 2:
If you were Warren Buffett, would you invest in this stock? Justify your decision.
prompt 3:
Perform a Technical Analysis for {stock_name} and identify the chart pattern it has formed.
prompt 4:
What is the latest news about {stock_name}?
prompt 5:
Conduct a Sentiment Analysis for {stock_name} based on the latest news and provide valid reasons for the sentiment classification (Positive, Negative, or Neutral).
prompt 6:
Provide the latest Indian stock market news in bullet points.



Clearly state ONLY whether I should BUY or AVOID this stock based on the above prompts with one line answer to each of the prompt and tell reason why (include numbers if you have).

example:
1️⃣ Fundamental Analysis
BUY — Robust free cash flow (~₹449 bn), net margins at ~19%, low debt (debt/EBITDA ~0.14), reasonable P/E (~25.6×) vs sector, with strong profitability and balance sheet .

2️⃣ Warren Buffett Style
BUY — TCS exhibits a durable moat, consistent earnings, high ROE (~50%), and substantial free cash flow—classic Buffett qualities .

3️⃣ Technical Analysis
AVOID — The stock is bearish in the short-term; it's below its 200-day MA (~₹3,886) and 52-week down ~10.7%, indicating potential continued weakness despite a neutral RSI (~49) .

4️⃣ Latest News
BUY — Expansion news: major realty spend (~₹4,500 cr), new 20‑acre Kolkata campus, multi-year AI/cloud tie-up with Microsoft, no breach from M&S hack .

5️⃣ Sentiment Analysis
NEUTRAL — Overall news is positive (growth projects, partnerships), but mixed with macro tech headwinds (post Accenture sell-off) and union pushback on staffing policies—balanced sentiment .

6️⃣ Latest Indian Market News
BUY — Indian IT sector pullback offers entry, and TCS remains a blue‑chip stable performer with solid dividend record, strong fundamentals amid volatile tech sentiment .
"""

INDIAN_STOCKS = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ITC": "ITC.NS",
    "SBIN": "SBIN.NS",
    "ICICIBANK": "ICICIBANK.NS"
}

def normalize_ticker(ticker: str, exchange: str) -> str:
    suffix_map = {
        "NSE": ".NS",
        "BSE": ".BO",
        "NASDAQ": "",
        "NYSE": "",
    }
    suffix = suffix_map.get(exchange.upper(), "")
    return f"{ticker.upper()}{suffix}"

def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "Ticker": ticker,
        "P/E": info.get("trailingPE", "N/A"),
        "P/B": info.get("priceToBook", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "Debt/Equity": info.get("debtToEquity", "N/A"),
        "Dividend Yield": info.get("dividendYield", "N/A"),
        "Gross Margin": info.get("grossMargins", "N/A"),
        "Net Margin": info.get("netMargins", "N/A"),
        "Operating Margin": info.get("operatingMargins", "N/A"),
        "Revenue": info.get("totalRevenue", "N/A"),
        "Free Cash Flow": info.get("freeCashflow", "N/A"),
    }

def ask_openai(prompt):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /analyze <TICKER> <EXCHANGE> to get stock analysis.")

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ticker_input, exchange = context.args[0], context.args[1]
        ticker = normalize_ticker(ticker_input, exchange)
        metrics = get_stock_data(ticker)
        stock_data = "\n".join([f"{k}: {v}" for k, v in metrics.items()])
        prompt = FUNDAMENTAL_PROMPT.format(stock_name=ticker, exchange=exchange, stock_data=stock_data)
        response = ask_openai(prompt)
        await update.message.reply_text(response[:4000])
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

async def batch_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = []
    for name, ticker in INDIAN_STOCKS.items():
        try:
            metrics = get_stock_data(ticker)
            stock_data = "\n".join([f"{k}: {v}" for k, v in metrics.items()])
            prompt = FUNDAMENTAL_PROMPT.format(stock_name=name, exchange="NSE", stock_data=stock_data)
            answer = ask_openai(prompt)
            summary_lines = answer.strip().split("\n")
            summary = "\n".join([line for line in summary_lines if line.strip()[:2] in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]])
            if not summary.strip():
                summary = "(No clear response. Possibly too long or malformed.)"
            results.append(f"📊 **{name}**\n{summary}")
        except Exception as e:
            results.append(f"⚠️ Error analyzing {name}: {e}")

    message = ""
    for r in results:
        if len(message + r) < 3900:
            message += "\n\n" + r
        else:
            await update.message.reply_text(message[:4000], parse_mode="Markdown")
            message = r
    if message:
        await update.message.reply_text(message[:4000], parse_mode="Markdown")

# async def main():
#     app = ApplicationBuilder().token(BOT_TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CommandHandler("analyze", analyze))
#     app.add_handler(CommandHandler("batch", batch_analyze))
#     await app.initialize()
#     await app.start()
#     print("✅ Bot is running")
#     await app.updater.start_polling()
#     await app.updater.idle()

# async def main():
#     app = ApplicationBuilder().token(BOT_TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CommandHandler("analyze", analyze))
#     app.add_handler(CommandHandler("batch", batch_analyze))
#     print("✅ Bot is running")
#     await app.run_polling()

# async def main():
#     app = ApplicationBuilder().token(BOT_TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CommandHandler("analyze", analyze))
#     app.add_handler(CommandHandler("batch", batch_analyze))

#     print("✅ Setting webhook...")
#     await app.bot.set_webhook(url=WEBHOOK_URL)
#     await app.start()
#     await app.updater.start_webhook(
#         listen="0.0.0.0",
#         port=int(os.environ.get("PORT", 8080)),
#         url_path="/webhook",
#         webhook_url=WEBHOOK_URL,
#     )
#     await app.updater.idle()

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(CommandHandler("batch", batch_analyze))

    print("✅ Setting webhook...")

    # ✅ Must explicitly initialize before starting in webhook mode
    await app.initialize()

    # Set webhook URL
    await app.bot.set_webhook(url=WEBHOOK_URL)

    # ✅ Start the app in webhook mode
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        url_path="/webhook",
        webhook_url=WEBHOOK_URL,
    )

    # Keep the bot running
    await app.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
