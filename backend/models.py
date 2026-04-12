"""
models.py
─────────
SQLAlchemy ORM models + SQLite-compatible schema.
Ready for PostgreSQL migration via DATABASE_URL env var.
"""

import os
import json
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Text, Boolean,
    DateTime, ForeignKey, JSON, UniqueConstraint, Index, Enum as SAEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

# ─── Database URL ─────────────────────────────────────────────────────────────

DB_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_DB = f"sqlite:///{os.path.join(DB_DIR, 'financial_ai.db')}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

# Fix for Render PostgreSQL URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Non-generator version for simple usage."""
    return SessionLocal()


# ─── Enums ────────────────────────────────────────────────────────────────────

class AssetClass(enum.Enum):
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    FOREX = "forex"
    CRYPTO = "crypto"
    OPTION = "option"


class TransactionType(enum.Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"


class AlertType(enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    VOLUME_SPIKE = "volume_spike"
    MA_CROSSOVER = "ma_crossover"
    BOLLINGER_BREAKOUT = "bollinger_breakout"
    PERCENT_CHANGE = "percent_change"


class AlertStatus(enum.Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    DISABLED = "disabled"


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), default="Investor")
    email = Column(String(200), default="")
    phone = Column(String(30), default="")
    risk_profile = Column(String(50), default="Moderate")
    investment_goal = Column(String(100), default="Wealth Creation")
    experience = Column(String(50), default="Intermediate")
    preferred_sectors = Column(Text, default="[]")  # JSON array
    avatar_color = Column(String(10), default="#00c896")
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "phone": self.phone, "risk_profile": self.risk_profile,
            "investment_goal": self.investment_goal, "experience": self.experience,
            "preferred_sectors": json.loads(self.preferred_sectors or "[]"),
            "avatar_color": self.avatar_color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1)
    name = Column(String(100), default="Default Portfolio")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")
    optimizations = relationship("OptimizationResult", back_populates="portfolio", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id, "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "holdings_count": len(self.holdings) if self.holdings else 0,
        }


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(30), nullable=False)
    asset_class = Column(String(20), default="equity")
    quantity = Column(Float, default=0)
    avg_cost = Column(Float, default=0)
    currency = Column(String(5), default="INR")
    added_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_symbol"),
    )

    def to_dict(self):
        return {
            "id": self.id, "portfolio_id": self.portfolio_id,
            "symbol": self.symbol, "asset_class": self.asset_class,
            "quantity": self.quantity, "avg_cost": self.avg_cost,
            "currency": self.currency,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(30), nullable=False)
    type = Column(String(10), nullable=False)  # buy, sell, dividend
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fees = Column(Float, default=0)
    notes = Column(Text, default="")
    executed_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="transactions")

    def to_dict(self):
        return {
            "id": self.id, "portfolio_id": self.portfolio_id,
            "symbol": self.symbol, "type": self.type,
            "quantity": self.quantity, "price": self.price,
            "fees": self.fees, "notes": self.notes,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(30), nullable=False)
    period = Column(String(10), nullable=False)
    searched_at = Column(DateTime, default=datetime.utcnow)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1)
    symbol = Column(String(30), nullable=False, unique=True)
    name = Column(String(200), default="")
    sector = Column(String(100), default="")
    asset_class = Column(String(20), default="equity")
    note = Column(Text, default="")
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "symbol": self.symbol, "name": self.name,
            "sector": self.sector, "asset_class": self.asset_class,
            "note": self.note, "target_price": self.target_price,
            "stop_loss": self.stop_loss,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1)
    symbol = Column(String(30), nullable=False)
    alert_type = Column(String(30), nullable=False)  # price_above, rsi_overbought, etc.
    condition = Column(String(200), default="")       # human-readable condition text
    threshold = Column(Float, nullable=True)
    status = Column(String(20), default="active")     # active, triggered, expired, disabled
    triggered_value = Column(Float, nullable=True)
    triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="alerts")
    notifications = relationship("Notification", back_populates="alert", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id,
            "symbol": self.symbol, "alert_type": self.alert_type,
            "condition": self.condition, "threshold": self.threshold,
            "status": self.status, "triggered_value": self.triggered_value,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
    alert = relationship("Alert", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id,
            "alert_id": self.alert_id, "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PriceCache(Base):
    __tablename__ = "price_cache"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(30), nullable=False)
    asset_class = Column(String(20), default="equity")
    date = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    source = Column(String(30), default="yfinance")

    __table_args__ = (
        UniqueConstraint("symbol", "date", "source", name="uq_price_symbol_date"),
        Index("ix_price_symbol_date", "symbol", "date"),
    )


class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    strategy = Column(String(50), nullable=False)
    symbols = Column(Text, default="[]")           # JSON array of symbols
    weights = Column(Text, default="{}")            # JSON dict {symbol: weight}
    expected_return = Column(Float)
    volatility = Column(Float)
    sharpe_ratio = Column(Float)
    var_95 = Column(Float)
    cvar_95 = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="optimizations")

    def to_dict(self):
        return {
            "id": self.id, "portfolio_id": self.portfolio_id,
            "strategy": self.strategy,
            "symbols": json.loads(self.symbols or "[]"),
            "weights": json.loads(self.weights or "{}"),
            "expected_return": self.expected_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "var_95": self.var_95, "cvar_95": self.cvar_95,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
        }


# ─── Create all tables ───────────────────────────────────────────────────────

def init_db():
    """Create all tables and ensure default user exists."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(id=1).first()
        if not user:
            session.add(User(id=1, name="Investor"))
            session.commit()
        # Ensure default portfolio
        portfolio = session.query(Portfolio).filter_by(user_id=1).first()
        if not portfolio:
            session.add(Portfolio(user_id=1, name="Default Portfolio"))
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"DB init warning: {e}")
    finally:
        session.close()
