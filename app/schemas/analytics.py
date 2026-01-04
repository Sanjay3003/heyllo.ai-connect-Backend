"""Analytics schemas"""

from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import date


class DashboardKPIs(BaseModel):
    """Dashboard KPI metrics"""
    total_calls: int
    answer_rate: float
    interested_leads: int
    avg_duration: str
    cost_per_lead: float
    total_calls_change: float
    answer_rate_change: float


class CallsOverTime(BaseModel):
    """Time series data for calls"""
    date: str
    calls: int
    answered: int
    interested: int


class OutcomeDistribution(BaseModel):
    """Call outcome distribution"""
    outcome: str
    count: int
    percentage: float


class SentimentData(BaseModel):
    """Sentiment analysis by hour"""
    hour: str
    positive: int
    neutral: int
    negative: int


class CampaignPerformance(BaseModel):
    """Campaign performance metrics"""
    name: str
    total_calls: int
    answered: int
    interested: int
    conversion_rate: float
    cost_per_lead: float
