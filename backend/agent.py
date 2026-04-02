import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from backend.tools import (
    get_stock_price,
    get_news_sentiment,
    get_rsi_and_ma,
    get_fundamental_analysis,
    get_sector_analysis,
    get_market_status,
)

load_dotenv()


def get_agent_executor():
    if not os.environ.get("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    tools = [
        get_stock_price,
        get_news_sentiment,
        get_rsi_and_ma,
        get_fundamental_analysis,
        get_sector_analysis,
        get_market_status,
    ]
    return create_react_agent(llm, tools)


def run_financial_agent(query: str) -> str:
    try:
        agent_executor = get_agent_executor()

        system_prompt = (
            "You are an expert financial AI assistant specialising in Indian stock markets (NSE/BSE). "
            "Your goal is to be as helpful as possible even when the user input is unclear. "
            "If a user asks about a stock or company but does not provide the exact ticker symbol, "
            "DO NOT ask them to clarify. Instead, intelligently infer the correct Yahoo Finance ticker "
            "symbol automatically. For example, if they say 'TCS' use 'TCS.NS', 'Reliance' → 'RELIANCE.NS', "
            "'HDFC Bank' → 'HDFCBANK.NS', 'Infosys' → 'INFY.NS'. "
            "Always include the .NS suffix for NSE-listed Indian stocks. "
            "When analysing a stock, proactively fetch both price data AND fundamental metrics. "
            "Always mention prices in INR (₹). "
            "Use get_market_status to check if the market is open when timing is relevant. "
            "Use get_sector_analysis for sector-wide comparisons. "
            "Always try to fulfill the request using the tools available."
        )

        response = agent_executor.invoke({
            "messages": [
                ("system", system_prompt),
                ("user", query),
            ]
        })

        content = response["messages"][-1].content
        if isinstance(content, list):
            texts = [
                part["text"]
                for part in content
                if isinstance(part, dict) and "text" in part
            ]
            return "\n".join(texts) if texts else str(content)
        return str(content)

    except ValueError as e:
        return f"Configuration Error: {e}"
    except Exception as e:
        return f"Error running agent: {e}"
