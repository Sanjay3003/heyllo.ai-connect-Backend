"""
Bland AI Client
Handles all interactions with Bland AI API for phone calls
"""

import httpx
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
from app.config import settings

class BlandAIClient:
    """Client for Bland AI API"""
    
    def __init__(self):
        # Use settings from config (which loads from .env)
        self.api_key = settings.BLAND_AI_API_KEY
        self.base_url = settings.BLAND_AI_BASE_URL
        
        self.headers = {
            "authorization": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def initiate_call(
        self,
        phone_number: str,
        task: str,
        voice: str = "nat",
        model: str = "enhanced",  # Use OpenAI model
        first_sentence: Optional[str] = None,
        wait_for_greeting: bool = True,
        record: bool = True,
        webhook: Optional[str] = None,
        metadata: Optional[Dict] = None,
        max_duration: int = 300,  # 5 minutes default
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Initiate a new outbound call with OpenAI GPT-4.1-mini
        
        Args:
            phone_number: E.164 format phone number (e.g., +12125551234)
            task: The AI agent's instructions/prompt (from AI Config page)
            voice: Voice to use (nat, josh, florian, derek, june, paige)
            model: AI model - use "enhanced" for GPT-4 level intelligence
            first_sentence: Opening line the AI should say
            wait_for_greeting: Wait for human to speak first
            record: Whether to record the call
            webhook: URL for webhook notifications
            metadata: Additional data to attach to call (lead_id, campaign_id, etc.)
            max_duration: Maximum call duration in seconds
            temperature: AI creativity (0.0-1.0, default 0.7)
            
        Returns:
            Dict with call_id and status
        """
        
        # Validate API key is configured
        if not self.api_key:
            raise ValueError(
                "Bland AI API key not configured. "
                "Please add BLAND_AI_API_KEY to your .env file"
            )
        
        # Build payload according to Bland AI API spec
        # https://docs.bland.ai/api-v1/post/calls
        payload = {
            "phone_number": phone_number,
            "task": task,
            "voice": voice,
            "wait_for_greeting": wait_for_greeting,
            "record": record,
            "max_duration": max_duration // 60 if max_duration > 60 else max_duration,  # API expects minutes
            "temperature": temperature,
            "language": "en-US",
        }
        
        if first_sentence:
            payload["first_sentence"] = first_sentence
        
        if webhook:
            payload["webhook"] = webhook
        
        if metadata:
            payload["metadata"] = metadata
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/calls",
                headers=self.headers,
                json=payload,
                timeout=30.0
            )
            
            # If error, try to get detailed error message
            if response.status_code >= 400:
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get("message", error_detail.get("error", str(error_detail)))
                    raise Exception(f"Bland AI Error: {error_msg}")
                except Exception as e:
                    if "Bland AI Error" in str(e):
                        raise
                    response.raise_for_status()
            
            return response.json()
    
    async def get_call_details(self, call_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a call
        
        Args:
            call_id: The Bland AI call ID
            
        Returns:
            Dict with call details including transcript, recording, etc.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/calls/{call_id}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Debug: Print what Bland AI returns
            print(f"[BLAND AI DEBUG] Call {call_id} response keys: {list(data.keys())}")
            print(f"[BLAND AI DEBUG] call_length: {data.get('call_length')}")
            print(f"[BLAND AI DEBUG] status: {data.get('status')}")
            print(f"[BLAND AI DEBUG] transcripts type: {type(data.get('transcripts'))}")
            print(f"[BLAND AI DEBUG] transcript type: {type(data.get('transcript'))}")
            
            # Check different possible field names for transcript
            if 'transcripts' in data:
                print(f"[BLAND AI DEBUG] transcripts length: {len(data.get('transcripts', []))}")
            if 'transcript' in data:
                print(f"[BLAND AI DEBUG] transcript preview: {str(data.get('transcript', ''))[:200]}")
            if 'concatenated_transcript' in data:
                print(f"[BLAND AI DEBUG] concatenated_transcript preview: {str(data.get('concatenated_transcript', ''))[:200]}")
            
            return data
    
    async def list_calls(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List recent calls
        
        Args:
            limit: Number of calls to return
            offset: Pagination offset
            
        Returns:
            List of call summaries
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/calls",
                headers=self.headers,
                params={"limit": limit, "offset": offset},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    def analyze_outcome(self, transcripts: List[Dict]) -> str:
        """
        Analyze call transcripts to determine outcome
        
        Args:
            transcripts: List of transcript objects from Bland AI
            
        Returns:
            Outcome string: 'interested', 'not_interested', 'callback', 'voicemail', 'no_answer', 'inconclusive'
        """
        if not transcripts:
            return "no_answer"
        
        # Combine all text
        full_text = " ".join([t.get("text", "") for t in transcripts]).lower()
        lead_texts = " ".join([t.get("text", "") for t in transcripts if t.get("user") == "user"]).lower()
        
        # Voicemail detection
        if len(transcripts) <= 2 and "voicemail" in full_text:
            return "voicemail"  
        
        # Keywords for different outcomes
        interested_keywords = [
            "interested", "yes", "sounds good", "let's do it", "schedule", 
            "when can", "what time", "sign up", "demo", "more information"
        ]
        not_interested_keywords = [
            "not interested", "no thanks", "not right now", "remove me", 
            "stop calling", "don't call", "unsubscribe"
        ]
        callback_keywords = [
            "call back", "later", "next week", "next month", "email me", 
            "send information", "busy right now"
        ]
        
        # Count matches
        interested_count = sum(1 for keyword in interested_keywords if keyword in lead_texts)
        not_interested_count = sum(1 for keyword in not_interested_keywords if keyword in lead_texts)
        callback_count = sum(1 for keyword in callback_keywords if keyword in lead_texts)
        
        # Determine outcome
        if interested_count > 0 and interested_count > not_interested_count:
            return "interested"
        elif not_interested_count > 0:
            return "not_interested"
        elif callback_count > 0:
            return "callback"
        else:
            return "inconclusive"
    
    def analyze_sentiment(self, transcripts: List[Dict]) -> str:
        """
        Analyze sentiment of the call
        
        Args:
            transcripts: List of transcript objects
            
        Returns:
            Sentiment: 'positive', 'negative', or 'neutral'
        """
        if not transcripts:
            return "neutral"
        
        # Get only lead's responses
        lead_texts = [t.get("text", "") for t in transcripts if t.get("user") == "user"]
        combined_text = " ".join(lead_texts).lower()
        
        if not combined_text:
            return "neutral"
        
        # Positive and negative indicators
        positive_words = [
            "yes", "great", "interested", "good", "sounds", "help", 
            "definitely", "perfect", "wonderful", "excellent", "thank"
        ]
        negative_words = [
            "no", "not", "busy", "don't", "won't", "can't", "sorry", 
            "annoyed", "stop", "never", "bad", "terrible"
        ]
        
        positive_count = sum(1 for word in positive_words if word in combined_text)
        negative_count = sum(1 for word in negative_words if word in combined_text)
        
        # Calculate sentiment
        if positive_count > negative_count + 1:
            return "positive"
        elif negative_count > positive_count + 1:
            return "negative"
        else:
            return "neutral"
    
    def calculate_cost(self, call_length_seconds: int, voice: str = "nat") -> int:
        """
        Calculate cost of a call in cents
        
        Args:
            call_length_seconds: Duration in seconds
            voice: Voice used
            
        Returns:
            Cost in cents (Integer)
        """
        # Bland AI pricing (cents per minute)
        rate_per_minute = 9  # Standard rate
        
        # Premium voices cost more
        if voice in ["paige", "june"]:
            rate_per_minute = 12
        
        minutes = call_length_seconds / 60
        return int(minutes * rate_per_minute)


# Global client instance
bland_client = BlandAIClient()
