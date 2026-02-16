"""
Stage 5: Gemini Grounded Review — Pubroot

PURPOSE:
    Send the assembled review prompt to Gemini 2.5 Flash-Lite with Google Search
    grounding. This single API call does BOTH the LLM review AND the web-based
    fact-checking. Gemini autonomously searches Google to verify factual claims
    and returns structured citations (groundingMetadata) mapping specific response
    segments to source URLs.
    
    This is the only stage that costs money (and even then it's $0 on the free tier).
    The free tier allows 1,500 grounded requests/day = 45,000/month.

CALLED BY:
    review_pipeline_main.py — passes the prompt string from Stage 4.

EXTERNAL APIS USED:
    - Gemini 2.5 Flash-Lite with Google Search grounding (google-genai Python SDK)
    - API key stored as GitHub Secret: GEMINI_API_KEY

COST:
    - Free tier: $0 (1,500 grounded requests/day)
    - Paid tier (if exceeded): $0.035 per grounded prompt + ~$0.0016 in tokens
    - Total per review on paid: ~$0.037

DESIGN DECISIONS:
    - We use google-genai (the newer SDK) NOT google-generativeai (legacy).
      The google-genai SDK is the current recommended SDK for Gemini API access
      as of early 2026 and supports grounding tools natively.
    - We force JSON output via response_mime_type="application/json" in the
      GenerateContentConfig. This ensures the response is always valid JSON
      even if the model would otherwise add prose around it.
    - We set temperature=0.2 for consistent, deterministic reviews. Higher
      temperatures would make reviews less reproducible.
    - We extract grounding metadata (search queries, source URLs, confidence
      mappings) and attach it to the review output. This metadata is stored
      alongside the review JSON for transparency and auditability.
    - If the Gemini call fails, we retry once. If it fails again, we return
      a structured error that Stage 6 will handle (post error comment, don't
      accept/reject).
    - We validate the JSON response against our expected schema. If the model
      produces malformed JSON, we attempt a simple fix (strip Markdown code
      fences) before giving up.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional


def run_gemini_grounded_review(
    review_prompt: str,
    gemini_api_key: str,
    model_name: str = "gemini-2.5-flash-lite",
    max_retries: int = 2
) -> dict:
    """
    Send the review prompt to Gemini with Google Search grounding and parse the result.
    
    This is the ONLY public function in this file. It handles the API call,
    response parsing, JSON validation, grounding metadata extraction, and
    error handling with retries.
    
    Args:
        review_prompt: The complete prompt string from Stage 4
        gemini_api_key: The Gemini API key (from GEMINI_API_KEY secret)
        model_name: The Gemini model to use. Default is gemini-2.5-flash-lite
                    which is the cheapest option with grounding support.
                    Can be overridden for "deep review" paid tier.
        max_retries: Number of times to retry on failure. Default 2 (total 2 attempts).
    
    Returns:
        dict with keys:
            - 'success' (bool): Whether the review completed successfully
            - 'review' (dict or None): The parsed review JSON from Gemini
            - 'grounding_metadata' (dict or None): Extracted grounding info
            - 'raw_response_text' (str): The raw text response from Gemini
            - 'model_used' (str): Which model was actually used
            - 'error' (str or None): Error message if failed
    """
    
    # -----------------------------------------------------------------------
    # Import google-genai here (not at module top) so the module can be
    # imported for testing even without the SDK installed. The SDK is only
    # available inside the GitHub Actions runner where it's pip-installed.
    # -----------------------------------------------------------------------
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {
            "success": False,
            "review": None,
            "grounding_metadata": None,
            "raw_response_text": "",
            "model_used": model_name,
            "error": (
                "google-genai SDK not installed. Run: pip install google-genai. "
                "This SDK is required for the Gemini API call with grounding."
            ),
        }
    
    # -----------------------------------------------------------------------
    # Configure the Gemini client
    # -----------------------------------------------------------------------
    # We pass the API key directly to the Client constructor.
    # In GitHub Actions, this comes from the GEMINI_API_KEY secret.
    # -----------------------------------------------------------------------
    
    client = genai.Client(api_key=gemini_api_key)
    
    # -----------------------------------------------------------------------
    # Configure the grounding tool and generation parameters
    # -----------------------------------------------------------------------
    # google_search=types.GoogleSearch() enables Google Search grounding.
    # The model will autonomously decide what to search based on the prompt.
    # It typically searches for factual claims it wants to verify.
    #
    # response_mime_type="application/json" forces the model to output valid
    # JSON. This is critical for our pipeline — we need parseable structured
    # data, not prose with JSON embedded in it.
    #
    # temperature=0.2 keeps reviews consistent and reproducible. The
    # calibration examples in the prompt further anchor scoring behavior.
    # -----------------------------------------------------------------------
    
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        response_mime_type="application/json",
        temperature=0.2,
    )
    
    # -----------------------------------------------------------------------
    # Make the API call with retry logic
    # -----------------------------------------------------------------------
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=review_prompt,
                config=config,
            )
            
            # Extract the text response
            raw_text = response.text if response.text else ""
            
            if not raw_text:
                last_error = "Gemini returned an empty response"
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                break
            
            # ---------------------------------------------------------------
            # Parse the JSON response
            # ---------------------------------------------------------------
            # The response should be valid JSON because we set
            # response_mime_type="application/json". But sometimes the model
            # wraps it in Markdown code fences (```json ... ```) despite the
            # MIME type setting. We handle that case.
            # ---------------------------------------------------------------
            
            review_json = _parse_review_json(raw_text)
            
            if review_json is None:
                last_error = f"Failed to parse Gemini response as JSON. Raw text: {raw_text[:500]}"
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
            # Extract grounding metadata
            # ---------------------------------------------------------------
            # Grounding metadata tells us what Google searches the model ran,
            # which URLs it found, and how specific response segments map to
            # sources. We store this alongside the review for transparency.
            # ---------------------------------------------------------------
            
            grounding = _extract_grounding_metadata(response)
            
            return {
                "success": True,
                "review": review_json,
                "grounding_metadata": grounding,
                "raw_response_text": raw_text,
                "model_used": model_name,
                "error": None,
            }
        
        except Exception as e:
            last_error = f"Gemini API call failed (attempt {attempt + 1}): {str(e)}"
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


def _extract_grounding_metadata(response) -> dict:
    """
    Extract grounding metadata from the Gemini response.
    
    Grounding metadata includes:
    - web_search_queries: What the model searched Google for
    - grounding_chunks: Source URLs and titles the model used
    - grounding_supports: Confidence mappings from response segments to sources
    
    This data is stored in reviews/{paper-id}/review.json for transparency.
    Agents consuming the review can verify claims by following the source URLs.
    
    We wrap this in a try/except because grounding metadata structure can vary
    between model versions, and we don't want metadata extraction failures
    to break the pipeline.
    """
    try:
        candidate = response.candidates[0] if response.candidates else None
        if not candidate:
            return {"available": False, "error": "No candidates in response"}
        
        metadata = candidate.grounding_metadata
        if not metadata:
            return {"available": False, "error": "No grounding metadata in response"}
        
        result = {"available": True}
        
        # Extract search queries
        if metadata.web_search_queries:
            result["web_search_queries"] = list(metadata.web_search_queries)
        
        # Extract grounding chunks (source URLs)
        sources = []
        if metadata.grounding_chunks:
            for chunk in metadata.grounding_chunks:
                if hasattr(chunk, "web") and chunk.web:
                    sources.append({
                        "title": getattr(chunk.web, "title", ""),
                        "uri": getattr(chunk.web, "uri", ""),
                    })
        result["sources"] = sources
        
        # Extract grounding supports (confidence mappings)
        supports = []
        if metadata.grounding_supports:
            for support in metadata.grounding_supports:
                support_data = {}
                if hasattr(support, "segment") and support.segment:
                    support_data["text"] = getattr(support.segment, "text", "")
                if hasattr(support, "confidence_scores"):
                    support_data["confidence_scores"] = list(support.confidence_scores) if support.confidence_scores else []
                if hasattr(support, "grounding_chunk_indices"):
                    support_data["chunk_indices"] = list(support.grounding_chunk_indices) if support.grounding_chunk_indices else []
                supports.append(support_data)
        result["supports"] = supports
        
        return result
    
    except Exception as e:
        return {
            "available": False,
            "error": f"Failed to extract grounding metadata: {str(e)}",
        }
