"""Output schema: one PostCard per input text."""
from enum import Enum

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Sentiment(str, Enum):
    bullish = "bullish"   # expects growth / suggests buying
    bearish = "bearish"   # expects decline / suggests selling
    neutral = "neutral"   # mentioned without an opinion (news, facts)
    mixed = "mixed"       # pros and cons


class Horizon(str, Enum):
    short = "short"       # days to weeks
    medium = "medium"     # months
    long = "long"         # a year or more
    unknown = "unknown"


class AssetType(str, Enum):
    stock = "stock"
    etf = "etf"
    index = "index"
    crypto = "crypto"
    private = "private"   # not publicly traded (Anthropic, OpenAI, SpaceX)
    other = "other"


class Language(str, Enum):
    uk = "uk"
    ru = "ru"
    en = "en"
    mixed = "mixed"
    unknown = "unknown"   # no words to judge by (emoji only)


TICKER_RE = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,9}")


# extra="forbid" -> additionalProperties: false, required by strict JSON schema mode
class StockMention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(description="Company name as written in the text")
    ticker: str | None = Field(description="Normalized ticker, e.g. NVDA; null if private or unknown")
    asset_type: AssetType
    sentiment: Sentiment
    reasoning: str | None = Field(description="Why the author thinks so, briefly, in Russian; null if no reason given")
    price_target: float | None = Field(description="Explicit price target if stated, else null")
    horizon: Horizon
    quote: str = Field(description="Exact quote from the text that supports this mention")

    # Checks the JSON schema cannot express; a violation triggers the repair attempt
    @field_validator("ticker")
    @classmethod
    def ticker_format(cls, v: str | None) -> str | None:
        if v is not None and (v.strip().lower() in {"null", "none", "n/a", ""}
                              or not TICKER_RE.fullmatch(v)):
            raise ValueError(f"ticker {v!r}: use an upper-case symbol without '$' (e.g. NVDA, BRK.B) or JSON null")
        return v


class PostCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Language
    is_about_stocks: bool = Field(description="True if the text discusses specific securities or markets")
    mentions: list[StockMention] = Field(description="Every company / security mentioned; empty if none")
    summary: str = Field(description="One sentence in Russian: what the text is about")


def json_schema() -> dict:
    """Schema in the shape OpenAI-compatible `response_format` expects."""
    return {
        "name": "PostCard",
        "strict": True,
        "schema": PostCard.model_json_schema(),
    }
