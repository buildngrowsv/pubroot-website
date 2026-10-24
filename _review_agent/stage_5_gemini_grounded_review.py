"""
Stage 5: OpenRouter LLM Review with Web Search — Pubroot

PURPOSE:
    Send the assembled review prompt to an LLM via OpenRouter with web search
    capabilities. OpenRouter provides unified API access to multiple LLM providers
    and includes web search grounding via the openrouter:web_search server tool.
    The LLM autonomously decides when to search the web to verify factual claims
    and returns structured citations (via annotations) mapping specific response
    segments to source URLs.
    
    This is the only stage that costs money. Cost varies by model choice.

CALLED BY:
    review_pipeline_main.py or stages_4_to_6_reviewer.py — passes the prompt string from Stage 4.

EXTERNAL APIS USED:
    - OpenRouter API (OpenAI-compatible endpoint at https://openrouter.ai/api/v1)
    - API key stored as GitHub Secret: OPENROUTER_API_KEY
    - Web search via openrouter:web_search server tool (default engine: auto)

COST (using default google/gemini-3.5-flash-lite):
    - Prompt: ~$0.30 per 1M tokens
    - Completion: ~$2.50 per 1M tokens
    - Web search: Additional cost per search (varies by engine, typically $0.005-0.01 per search)
    - Estimated per review: ~$0.02-0.05 depending on prompt size and web search usage

DESIGN DECISIONS:
    - We use the OpenAI Python SDK configured for OpenRouter's base URL.
      OpenRouter is OpenAI-compatible, so we can use the official openai SDK.
    - Default model is google/gemini-3.5-flash-lite via OpenRouter, which provides
      similar capabilities and cost profile to the old direct Gemini setup.
    - Model is configurable via PUBROOT_MODEL env var or model_name parameter.
    - We use the openrouter:web_search server tool (not deprecated :online or web plugin).
      The model decides when and how often to search based on the prompt.
    - OpenRouter attribution headers (HTTP-Referer, X-Title) are sent per OpenRouter docs.
    - We set temperature=0.2 for consistent, deterministic reviews.
    - We use JSON mode (response_format={"type": "json_object"}) to enforce structured output.
    - We extract web search metadata from response annotations and map it to our
      grounding_metadata format for backward compatibility with Stage 6.
    - If the API call fails, we retry with exponential backoff. If all retries fail,
      we return a structured error that Stage 6 will handle (post error comment).
    - We validate the JSON response against our expected schema. If the model produces
      malformed JSON, we attempt a simple fix (strip Markdown code fences) before giving up.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


def run_openrouter_review(
    review_prompt: str,
    openrouter_api_key: str,
    model_name: str = "google/gemini-3.5-flash-lite",
    max_retries: int = 2
) -> dict:
    """
    Send the review prompt to OpenRouter with web search and parse the result.
    
    This is the ONLY public function in this file. It handles the API call,
    response parsing, JSON validation, web search metadata extraction, and
    error handling with retries.
    
    Args:
        review_prompt: The complete prompt string from Stage 4
        openrouter_api_key: The OpenRouter API key (from OPENROUTER_API_KEY secret)
        model_name: The model to use via OpenRouter. Default is google/gemini-3.5-flash-lite.
                    Can be overridden via PUBROOT_MODEL env var or parameter.
        max_retries: Number of times to retry on failure. Default 2 (total 2 attempts).
    
    Returns:
        dict with keys:
            - 'success' (bool): Whether the review completed successfully
            - 'review' (dict or None): The parsed review JSON
            - 'grounding_metadata' (dict or None): Extracted web search info
            - 'raw_response_text' (str): The raw text response
            - 'model_used' (str): Which model was actually used
            - 'error' (str or None): Error message if failed
    """
    
    # -----------------------------------------------------------------------
    # Import OpenAI SDK here (not at module top) so the module can be
    # imported for testing even without the SDK installed. The SDK is only
    # available inside the GitHub Actions runner where it's pip-installed.
    # -----------------------------------------------------------------------
    try:
        from openai import OpenAI
    except ImportError:
        return {
            "success": False,
            "review": None,
            "grounding_metadata": None,
            "raw_response_text": "",
            "model_used": model_name,
            "error": (
                "openai SDK not installed. Run: pip install openai. "
                "This SDK is required for the OpenRouter API call."
            ),
        }
    
    # -----------------------------------------------------------------------
    # Configure the OpenRouter client
    # -----------------------------------------------------------------------
    # OpenRouter is OpenAI-compatible, so we use the OpenAI SDK with a custom
    # base URL. In GitHub Actions, the API key comes from the OPENROUTER_API_KEY secret.
    # We also send attribution headers per OpenRouter documentation.
    # -----------------------------------------------------------------------
    
    client = OpenAI(
        api_key=openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://pubroot.com",
            "X-Title": "Pubroot AI Peer Review",
        }
    )
    
    # -----------------------------------------------------------------------
    # Configure request parameters and web search tool
    # -----------------------------------------------------------------------
    # The openrouter:web_search server tool enables web search grounding.
    # The model autonomously decides when to search based on the prompt.
    # The default engine is "auto", which uses native provider search when
    # available (for Gemini via Google) and falls back to Exa otherwise.
    #
    # temperature=0.2 keeps reviews consistent and reproducible. The
    # calibration examples in the prompt further anchor scoring behavior.
    #
    # response_format={"type": "json_object"} forces JSON output. This is
    # critical for our pipeline — we need parseable structured data.
    #
    # max_tokens is set to 16384 to allow for detailed claim-level analysis
    # without truncation. In March 2026, truncated responses caused parser
    # failures on high-scoring articles with verbose analysis.
    # -----------------------------------------------------------------------
    
    # Web search tool configuration (OpenRouter server tool, not deprecated plugin)
    web_search_tool = {
        "type": "openrouter:web_search",
        "parameters": {
            "engine": "auto",  # Use native provider search (Google for Gemini) or Exa fallback
            "max_results": 5,   # Results per search call
            "max_total_results": 20,  # Total results across all searches in one request
        }
    }

    last_error = None
    
    for attempt in range(max_retries):
        try:
            # OpenRouter API call using OpenAI SDK
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": review_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=16384,
                response_format={"type": "json_object"},
                tools=[web_search_tool]
            )
            
            # Extract the text response
            if not response.choices or not response.choices[0].message:
                last_error = "OpenRouter returned empty response.choices"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                break
            
            message = response.choices[0].message
            raw_text = message.content or ""
            
            if not raw_text:
                last_error = "OpenRouter returned an empty message.content"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                break
            
            # ---------------------------------------------------------------
            # Parse the JSON response
            # ---------------------------------------------------------------
            # The response should be valid JSON because we set
            # response_format={"type": "json_object"}. But we still handle
            # cases where the model wraps it in Markdown code fences.
            # ---------------------------------------------------------------
            
            review_json = _parse_review_json(raw_text)
            
            if review_json is None:
                last_error = f"Failed to parse OpenRouter response as JSON. Raw text: {raw_text[:500]}"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                break
            
            # ---------------------------------------------------------------
            # Validate the review JSON has required fields
            # ---------------------------------------------------------------
            
            validation_errors = _validate_review_schema(review_json)
            if validation_errors:
                last_error = f"Review JSON missing required fields: {', '.join(validation_errors)}"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                # On last attempt, accept partial JSON rather than failing entirely
                # The pipeline can still work with incomplete data
            
            # ---------------------------------------------------------------
            # Extract web search metadata from annotations
            # ---------------------------------------------------------------
            # OpenRouter returns web search results in message.annotations
            # (url_citation format). We extract this and map it to our
            # grounding_metadata format for backward compatibility with Stage 6.
            # ---------------------------------------------------------------
            
            grounding = _extract_web_search_metadata(response)
            
            return {
                "success": True,
                "review": review_json,
                "grounding_metadata": grounding,
                "raw_response_text": raw_text,
                "model_used": model_name,
                "error": None,
            }
        
        except Exception as e:
            err_text = str(e)
            last_error = f"OpenRouter API call failed (attempt {attempt + 1}): {err_text}"
            
            # Check for rate limiting or quota errors
            is_rate_limit = (
                "429" in err_text
                or "rate" in err_text.lower()
                or "quota" in err_text.lower()
            )
            
            if is_rate_limit:
                last_error += " (rate limit or quota exceeded)"
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                continue
    
    # All retries failed
    return {
        "success": False,
        "review": None,
        "grounding_metadata": None,
        "raw_response_text": "",
        "model_used": model_name,
        "error": last_error,
    }


# ---------------------------------------------------------------------------
# PRIVATE HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def _parse_review_json(raw_text: str) -> Optional[dict]:
    """
    Parse the Gemini response text into a JSON dict.
    
    Handles several common response formats:
    1. Clean JSON (ideal case — response_mime_type forces this)
    2. JSON wrapped in Markdown code fences (```json ... ```)
    3. JSON with leading/trailing whitespace or BOM
    
    Returns:
        Parsed dict, or None if parsing fails.
    """
    text = raw_text.strip()
    
    # Try direct parse first (most common with response_mime_type set)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try stripping Markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        if lines[-1].strip() == "```":
            inner = "\n".join(lines[1:-1])
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                pass
    
    # Try finding JSON object in the text (between first { and last })
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    return None


def _validate_review_schema(review: dict) -> list:
    """
    Check that the review JSON has the required fields.
    
    We don't enforce every single field — just the critical ones needed
    for the pipeline to make an accept/reject decision and produce meaningful
    output. Missing optional fields are acceptable.
    
    Returns:
        List of missing field names. Empty list means valid.
    """
    required_fields = ["score", "verdict", "summary"]
    missing = []
    
    for field in required_fields:
        if field not in review:
            missing.append(field)
    
    # Validate score is a number
    if "score" in review:
        try:
            score = float(review["score"])
            if score < 0 or score > 10:
                missing.append("score (must be 0.0-10.0)")
        except (TypeError, ValueError):
            missing.append("score (must be a number)")
    
    # Validate verdict is ACCEPTED or REJECTED
    if "verdict" in review:
        if review["verdict"] not in ("ACCEPTED", "REJECTED"):
            missing.append("verdict (must be ACCEPTED or REJECTED)")
    
    return missing


def _extract_web_search_metadata(response) -> dict:
    """
    Extract web search metadata from the OpenRouter response annotations.
    
    OpenRouter returns web search results in message.annotations with type
    "url_citation". Each annotation contains:
    - text: The segment of the response that cites this source
    - url: The source URL
    - title: The source title (if available)
    - start_index/end_index: Character positions in the response text
    
    We map this to our grounding_metadata format for backward compatibility:
    - available: bool (true if any citations exist)
    - sources: list of {uri, title} dicts
    - supports: list of {text, url} dicts mapping response segments to sources
    - web_search_queries: Not directly available from OpenRouter annotations,
      but we can infer that searches occurred if citations exist
    
    This data is stored in reviews/{paper-id}/review.json for transparency.
    
    We wrap this in a try/except because annotation structure can vary,
    and we don't want metadata extraction failures to break the pipeline.
    """
    try:
        if not response.choices or not response.choices[0].message:
            return {"available": False, "error": "No message in response"}
        
        message = response.choices[0].message
        annotations = getattr(message, "annotations", None) or []
        
        if not annotations:
            return {
                "available": False,
                "error": "No annotations in response (web search may not have been used)"
            }
        
        # Extract unique sources and citation mappings
        sources = []
        supports = []
        seen_urls = set()
        
        for annotation in annotations:
            # OpenRouter annotations use "url_citation" type for web search results
            if hasattr(annotation, "type") and annotation.type == "url_citation":
                url = getattr(annotation, "url", "")
                title = getattr(annotation, "title", "")
                text = getattr(annotation, "text", "")
                
                # Add to sources list (deduplicated by URL)
                if url and url not in seen_urls:
                    sources.append({
                        "uri": url,
                        "title": title or url,  # Fall back to URL if no title
                    })
                    seen_urls.add(url)
                
                # Add to supports (citation mappings)
                if text and url:
                    supports.append({
                        "text": text,
                        "url": url,
                        "title": title or url,
                    })
        
        if not sources:
            return {
                "available": False,
                "error": "No url_citation annotations found (web search may not have been used)"
            }
        
        return {
            "available": True,
            "sources": sources,
            "supports": supports,
            # web_search_queries not directly available from OpenRouter, but we know
            # searches occurred if we have citations
            "web_search_queries": ["(inferred from citations)"] if sources else [],
        }
    
    except Exception as e:
        return {
            "available": False,
            "error": f"Failed to extract web search metadata: {str(e)}",
        }


# Backward compatibility alias for old function name (for tests and imports)
run_gemini_grounded_review = run_openrouter_review
