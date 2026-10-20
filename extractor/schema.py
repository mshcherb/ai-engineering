"""Output schema: one PostCard per input text."""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
