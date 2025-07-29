import os
import requests
import yfinance as yf
import streamlit as st
from dotenv import load_dotenv
import plotly.graph_objects as go

# ----------------- LOAD API KEY -----------------

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"

# ----------------- GROQ CHAT FUNCTION -----------------

def ask_groq(prompt, temperature=0.7):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful AI financial advisor."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Groq API Error: {str(e)}"

# ----------------- STOCK HELPERS -----------------

def compare_stocks(symbols):
    data = {}
    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="6mo")
            if hist.empty:
                continue
            data[symbol] = hist['Close'].pct_change().sum()
        except Exception as e:
            print(f"{symbol} error: {e}")
            continue
    return data

def get_company_info(symbol):
    stock = yf.Ticker(symbol)
    return {
        "name": stock.info.get("longName", symbol),
        "sector": stock.info.get("sector", "N/A"),
        "market_cap": stock.info.get("marketCap", "N/A"),
        "summary": stock.info.get("longBusinessSummary", "N/A"),
    }

def get_company_news(symbol):
    stock = yf.Ticker(symbol)
    return stock.news[:5] if hasattr(stock, "news") else []

# ----------------- AI LOGIC LAYERS -----------------

def get_market_analysis(symbols):
    data = compare_stocks(symbols)
    if not data:
        return "No valid stock data found."
    return ask_groq(f"Compare these stock performances over the last 6 months: {data}")

def get_company_analysis(symbol):
    info = get_company_info(symbol)
    news = get_company_news(symbol)
    prompt = (
        f"Analyze the following company:\n"
        f"Name: {info['name']}\n"
        f"Sector: {info['sector']}\n"
        f"Market Cap: {info['market_cap']}\n"
        f"Summary: {info['summary']}\n"
        f"Recent News: {news}"
    )
    return ask_groq(prompt)

def get_stock_recommendations(symbols):
    analysis = get_market_analysis(symbols)
    company_data = {symbol: get_company_analysis(symbol) for symbol in symbols}
    prompt = f"""
    Based on this market analysis: {analysis}
    And the following company data: {company_data}
    Which stocks would you recommend to invest in and why?
    """
    return ask_groq(prompt)

def get_final_report(symbols):
    market = get_market_analysis(symbols)
    companies = [get_company_analysis(s) for s in symbols]
    recs = get_stock_recommendations(symbols)
    final_prompt = f"""
    Market Overview:
    {market}

    Company Profiles:
    {companies}

    Recommendations:
    {recs}

    Now, generate a complete investment report including performance, fundamentals, and a ranked list of the top stocks.
    """
    return ask_groq(final_prompt)

# ----------------- STREAMLIT UI -----------------

st.set_page_config(page_title="AI Investment Strategist", page_icon="📈", layout="wide")

# Header
st.markdown("""
    <div style="text-align: center;">
        <h1 style="color:#4CAF50;">📈 AI Investment Strategist</h1>
        <h4 style="color:#6c757d;">Personalized investment reports using AI & real stock data (Groq)</h4>
    </div>
""", unsafe_allow_html=True)

# Sidebar Input
st.sidebar.markdown("## 🧠 Enter Stock Symbols")
input_symbols = st.sidebar.text_input("Example: AAPL, TSLA, GOOG", "AAPL, TSLA, GOOG")
api_check = os.getenv("GROQ_API_KEY")
symbols = [s.strip().upper() for s in input_symbols.split(",") if s.strip()]
generate = st.sidebar.button("🚀 Generate AI Investment Report")

if generate:
    if not api_check:
        st.sidebar.error("❌ No API key detected in `.env` file.")
    elif not symbols:
        st.sidebar.error("⚠️ Please enter at least one valid stock symbol.")
    else:
        with st.spinner("🔍 Groq AI is analyzing market fundamentals..."):
            report = get_final_report(symbols)

        st.success("✅ Report Generated Successfully!")
        st.balloons()

        # Display Final Report
        st.markdown("## 📊 Final Investment Report")
        st.markdown(report)

        # Download Option
        st.download_button(
            label="📥 Download Report",
            data=report,
            file_name="investment_report.txt",
            mime="text/plain"
        )

        # Stock Price Comparison Chart
        st.markdown("---")
        st.markdown("## 📈 Stock Price Comparison (Last 6 Months)")

        df = yf.download(symbols, period="6mo")['Close']

        if df.empty:
            st.warning("No historical data available for the selected stocks.")
        else:
            fig = go.Figure()
            for symbol in symbols:
                fig.add_trace(go.Scatter(x=df.index, y=df[symbol], mode='lines', name=symbol))
            fig.update_layout(
                template="plotly_white",
                xaxis_title="Date",
                yaxis_title="Price (USD)",
                legend_title="Stock Symbol",
                hovermode="x unified",
                margin=dict(t=40, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)

            # Relative Return Ranking
            returns = df.pct_change().sum().sort_values(ascending=False)
            st.markdown("### 📉 Relative 6-Month Performance Ranking")
            st.dataframe(returns.to_frame("Return %").style.format("{:.2%}"))

            # Expandable Raw Data Viewer
            with st.expander("🔍 View Raw Price Data"):
                st.dataframe(df.style.format("${:.2f}"))
