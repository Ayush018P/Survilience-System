"""
NeuroGuard AI - LLM Service (Groq)
==================================
Handles interactions with the Groq API for the AI Security Assistant.
"""

import json
from groq import Groq
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model = "llama-3.1-8b-instant"  # Fast, highly capable open model

    def is_configured(self):
        return self.client is not None

    def query_assistant(self, user_query: str, context_data: dict) -> str:
        """
        Query the Groq API with context from the surveillance system.
        """
        if not self.is_configured():
            return "Error: Groq API key is not configured in the backend environment."

        system_prompt = (
            "You are the NeuroGuard AI Security Assistant. "
            "You are monitoring a privacy-first offline AI surveillance platform. "
            "You will be provided with JSON context containing recent security events, threats, and system metrics. "
            "Answer the user's questions clearly, concisely, and professionally based ONLY on the provided context. "
            "If the context does not contain the answer, say you don't have that information in recent logs."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"System Context (JSON):\n{json.dumps(context_data, indent=2)}\n\nUser Query: {user_query}"}
        ]

        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.2,
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return f"Error communicating with the AI Assistant service: {str(e)}"

    def generate_daily_summary(self, context_data: dict) -> str:
        """
        Generate an automated daily security report.
        """
        if not self.is_configured():
            return "Error: Groq API key is not configured."

        system_prompt = (
            "You are the NeuroGuard AI Security Analyst. "
            "Generate a highly professional, well-formatted Executive Security Summary for today. "
            "Use markdown formatting. Include sections for: Executive Summary, Key Anomalies, and Recommendations. "
            "Base your report entirely on the provided JSON data."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Daily Security Data (JSON):\n{json.dumps(context_data, indent=2)}"}
        ]

        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.3,
                max_tokens=2048,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return f"Error generating report: {str(e)}"

llm_service = LLMService()
