import os
import openai
import yfinance as yf
import streamlit as st
from dotenv import load_dotenv
import plotly.graph_objects as go

# Load API Key
load_dotenv()
from openai import OpenAI

client = OpenAI()

def ask_openai(prompt, model="gpt-3.5-turbo", temperature=0.7):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI financial advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI Error: {str(e)}"

        return f"Error: {str(e)}"

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

# ----------------- ANALYSIS LAYERS -----------------

def get_market_analysis(symbols):
    data = compare_stocks(symbols)
    if not data:
        return "No valid stock data found."
    return ask_openai(f"Compare these stock performances: {data}")

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
    return ask_openai(prompt)

def get_stock_recommendations(symbols):
    analysis = get_market_analysis(symbols)
    company_data = {symbol: get_company_analysis(symbol) for symbol in symbols}
    prompt = f"""
    Based on this market analysis: {analysis}
    And the following company data: {company_data}
    Which stocks would you recommend to invest in and why?
    """
    return ask_openai(prompt)

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
    return ask_openai(final_prompt)

# ----------------- STREAMLIT UI -----------------

st.set_page_config(page_title="AI Investment Strategist", page_icon="📈", layout="wide")

st.markdown("""
    <h1 style="text-align: center; color: #4CAF50;">📈 AI Investment Strategist</h1>
    <h3 style="text-align: center; color: #6c757d;">Personalized investment reports using AI & real stock data</h3>
""", unsafe_allow_html=True)

st.sidebar.markdown("## 🧠 Enter Stock Symbols (comma separated)")
input_symbols = st.sidebar.text_input("Example: AAPL, TSLA, GOOG", "AAPL, TSLA, GOOG")
api_check = os.getenv("OPENAI_API_KEY")
symbols = [s.strip().upper() for s in input_symbols.split(",")]

if st.sidebar.button("🧠 Generate AI Investment Report"):
    if not api_check:
        st.sidebar.warning("No API key detected in `.env` file.")
    elif not symbols:
        st.sidebar.warning("Please enter at least one stock symbol.")
    else:
        with st.spinner("Analyzing market and company fundamentals..."):
            report = get_final_report(symbols)
        st.subheader("📊 Final Investment Report")
        st.markdown(report)

        st.markdown("---")
        st.markdown("### 📈 Stock Price Comparison (Last 6 Months)")
        df = yf.download(symbols, period="6mo")['Close']
        fig = go.Figure()
        for symbol in symbols:
            fig.add_trace(go.Scatter(x=df.index, y=df[symbol], mode='lines', name=symbol))
        fig.update_layout(template="plotly_dark", xaxis_title="Date", yaxis_title="Price (USD)")
        st.plotly_chart(fig)
