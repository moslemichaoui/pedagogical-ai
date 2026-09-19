"""Google Gemini provider for pedagogical AI generation."""
import os
import json
from typing import Optional, Dict, Any


class GeminiProvider:
    """Google Gemini provider for pedagogical content generation."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the Gemini provider.
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Gemini model to use (defaults to GEMINI_MODEL env var or gemini-3.6-flash)
        """
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.model = model or os.environ.get('GEMINI_MODEL') or 'gemini-3.6-flash'
        self._client = None
    
    def is_available(self) -> bool:
        """Check if the provider is properly configured."""
        return bool(self.api_key and self.api_key != 'your-gemini-api-key-here')
    
    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is not None:
            return self._client
        
        if not self.is_available():
            raise RuntimeError(
                "Gemini API key required. "
                "Set GEMINI_API_KEY environment variable."
            )
        
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            return self._client
        except ImportError as e:
            raise RuntimeError(
                "google-genai package not installed. "
                "Please install it with: pip install google-genai"
            ) from e
    
    def generate(self, prompt: str, model: Optional[str] = None) -> str:
        """Generate text based on a prompt.
        
        Args:
            prompt: The prompt to send
            model: Gemini model to use (defaults to instance model)
            
        Returns:
            Generated text response
        """
        client = self._get_client()
        model_to_use = model or self.model
        
        try:
            response = client.models.generate_content(
                model=model_to_use,
                contents=prompt
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini generation failed: {str(e)}")
    
    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured JSON response based on a prompt.
        
        Args:
            prompt: The prompt to send
            schema: Optional JSON schema for structured output
            model: Gemini model to use (defaults to instance model)
            
        Returns:
            Parsed JSON response
        """
        text = self.generate(prompt, model=model)
        
        # Try to parse JSON from the response
        try:
            # Find JSON in the response text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": "Failed to parse response as JSON", "raw_response": text}
    
    def generate_with_structure(
        self,
        prompt: str,
        structure: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured content based on a schema.
        
        Args:
            prompt: The prompt to send
            structure: Expected structure description
            model: Gemini model to use (defaults to instance model)
            
        Returns:
            Structured response following the schema
        """
        # Build a prompt that explicitly requests structured output
        structured_prompt = f"""
{prompt}

IMPORTANT: Respond with valid JSON only. The response must follow this structure:
{json.dumps(structure, ensure_ascii=False, indent=2)}

Do not include any text before or after the JSON response.
"""
        return self.generate_json(structured_prompt, model=model)
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the provider is healthy."""
        if not self.is_available():
            return {
                'status': 'not_configured',
                'error': 'GEMINI_API_KEY not set'
            }
        try:
            self._get_client()
            return {'status': 'healthy'}
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }