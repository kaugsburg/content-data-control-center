import json
import anthropic
import config

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

# Tool definition — Claude must call this to return extracted data.
# Using tool_use forces structured JSON output without needing beta features.
_EXTRACTION_TOOL = {
    "name": "extract_page_data",
    "description": (
        "Extract all data points from the article that could be compared against "
        "internal reference data. Only extract values explicitly stated on the page — "
        "do not infer or fabricate. For each data point, also capture a short "
        "context_snippet (the surrounding sentence or phrase, ~20-40 words) so we "
        "can locate it on the page later."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_title": {
                "type": "string",
                "description": "The title of the article"
            },
            "companies": {
                "type": "array",
                "description": "Company-specific data points found on the page",
                "items": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "bbb_score": {
                            "type": ["string", "null"],
                            "description": "BBB letter grade, e.g. 'A+', 'A', 'B'"
                        },
                        "bbb_context": {
                            "type": ["string", "null"],
                            "description": "Surrounding text where the BBB score appears"
                        },
                        "rating": {
                            "type": ["number", "null"],
                            "description": "Numeric rating, e.g. 4.2"
                        },
                        "rating_scale": {
                            "type": ["string", "null"],
                            "description": "Rating scale, e.g. '/5' or '/10'"
                        },
                        "rating_context": {
                            "type": ["string", "null"],
                            "description": "Surrounding text where the rating appears"
                        },
                        "cost_low": {
                            "type": ["number", "null"],
                            "description": "Low end of a cost range in dollars (number only, no $ sign)"
                        },
                        "cost_high": {
                            "type": ["number", "null"],
                            "description": "High end of a cost range in dollars"
                        },
                        "cost_avg": {
                            "type": ["number", "null"],
                            "description": "Average cost in dollars if only one figure given"
                        },
                        "cost_unit": {
                            "type": ["string", "null"],
                            "description": "Unit for cost, e.g. 'per window', 'per project'"
                        },
                        "cost_context": {
                            "type": ["string", "null"],
                            "description": "Surrounding text where the cost appears"
                        },
                        "lawsuit_mentioned": {
                            "type": ["boolean", "null"],
                            "description": "True if a lawsuit or legal issue is mentioned for this company"
                        },
                        "lawsuit_summary": {
                            "type": ["string", "null"],
                            "description": "Brief summary of the lawsuit or legal issue"
                        },
                        "lawsuit_context": {
                            "type": ["string", "null"],
                            "description": "Surrounding text where the lawsuit is mentioned"
                        }
                    },
                    "required": ["company_name"]
                }
            },
            "general_costs": {
                "type": "array",
                "description": "Category-level cost data NOT tied to a specific company",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Service category, e.g. 'Window Replacement', 'Gutter Installation'"
                        },
                        "cost_low": {"type": ["number", "null"]},
                        "cost_high": {"type": ["number", "null"]},
                        "cost_avg": {"type": ["number", "null"]},
                        "unit": {
                            "type": ["string", "null"],
                            "description": "e.g. 'per window', 'per linear foot', 'whole home'"
                        },
                        "context_snippet": {
                            "type": ["string", "null"],
                            "description": "Surrounding text where this cost appears"
                        }
                    },
                    "required": ["category"]
                }
            }
        },
        "required": ["page_title", "companies", "general_costs"]
    }
}

# System prompt is static — set as a cache-eligible block to reduce API cost
# on repeated runs.
_SYSTEM_PROMPT = (
    "You are a data extraction assistant for a content team. "
    "Your job is to read article text and extract specific factual data points: "
    "BBB scores, company ratings, cost figures, survey statistics, and lawsuit mentions. "
    "Extract ONLY values that are explicitly stated in the text. "
    "Do not guess, infer, or hallucinate values. "
    "If a value is not present, return null for that field. "
    "For context_snippet fields, copy the exact sentence or phrase from the article "
    "where the data point appears — this must be a verbatim substring of the article text."
)


def extract_data_from_page(page_text: str) -> dict:
    """
    Send page text to Claude and return structured extracted data.
    Returns the tool input dict with keys: page_title, companies, general_costs.
    """
    response = _client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # cache the static system prompt
            }
        ],
        tools=[_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "extract_page_data"},
        messages=[
            {
                "role": "user",
                "content": f"Please extract all data points from the following article:\n\n{page_text}",
            }
        ],
    )

    # The model must have called our tool — find the tool_use block
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_page_data":
            return block.input

    # Should not happen given tool_choice, but return empty structure as fallback
    return {"page_title": "", "companies": [], "general_costs": []}
