import json
from openai import OpenAI
import config

_client = OpenAI(
    api_key=config.OPENAI_API_KEY,
)

_EXTRACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_page_data",
        "description": (
            "Extract all data points from the page content. "
            "Only extract values explicitly stated — do not infer or fabricate."
        ),
        "parameters": {
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
                                "description": "BBB letter grade, e.g. 'A+', 'A', 'B', 'NR'"
                            },
                            "bbb_context": {
                                "type": ["string", "null"],
                                "description": "Exact line or phrase from the page where the BBB score appears"
                            },
                            "rating": {
                                "type": ["number", "null"],
                                "description": "Numeric overall rating, e.g. 4.2"
                            },
                            "rating_scale": {
                                "type": ["string", "null"],
                                "description": "Rating scale, e.g. '/5' or '/10'"
                            },
                            "rating_context": {
                                "type": ["string", "null"],
                                "description": "Exact line or phrase from the page where the rating appears"
                            },
                            "lawsuit_mentioned": {
                                "type": ["boolean", "null"],
                                "description": "True if a lawsuit or legal issue is mentioned for this company"
                            },
                            "lawsuit_summary": {
                                "type": ["string", "null"],
                                "description": "Brief summary of the lawsuit"
                            },
                            "lawsuit_context": {
                                "type": ["string", "null"],
                                "description": "Exact line or phrase from the page where the lawsuit is mentioned"
                            }
                        },
                        "required": ["company_name"]
                    }
                },
                "cost_mentions": {
                    "type": "array",
                    "description": (
                        "Every cost or price figure found on the page — both company-specific "
                        "and general category costs. For each one, describe WHAT the cost is for "
                        "based on the surrounding text, not a predefined category."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": (
                                    "A plain-English description of what this cost is for, "
                                    "derived from the surrounding text. "
                                    "Examples: 'window replacement per window', "
                                    "'gutter installation whole home', "
                                    "'American Home Shield monthly cost', "
                                    "'Choice Home Warranty service fee'"
                                )
                            },
                            "company": {
                                "type": ["string", "null"],
                                "description": "Company name if this cost is tied to a specific company, otherwise null"
                            },
                            "cost_low": {
                                "type": ["number", "null"],
                                "description": "Low end of cost range in dollars (number only)"
                            },
                            "cost_high": {
                                "type": ["number", "null"],
                                "description": "High end of cost range in dollars (number only)"
                            },
                            "cost_avg": {
                                "type": ["number", "null"],
                                "description": "Single average or typical cost if only one figure given"
                            },
                            "unit": {
                                "type": ["string", "null"],
                                "description": "Unit of measurement, e.g. 'per window', 'per linear foot', 'per month', 'per claim'"
                            },
                            "context_snippet": {
                                "type": ["string", "null"],
                                "description": "The exact line or phrase from the page where this cost appears"
                            }
                        },
                        "required": ["label"]
                    }
                }
            },
            "required": ["page_title", "companies", "cost_mentions"]
        }
    }
}

_SYSTEM_PROMPT = (
    "You are a data extraction assistant for a content team. "
    "You will receive structured text extracted from a published article page. "
    "Table rows are formatted as: Column1 | Column2 | Column3. "
    "List items are prefixed with a bullet (•). "
    "Your job is to extract: "
    "(1) Company-specific data: BBB scores, star ratings, lawsuit mentions. "
    "(2) Every cost or price figure on the page — read the surrounding text to understand "
    "what each cost is for and describe it in plain English as the label. "
    "Do not force costs into predefined categories — let the page language guide the label. "
    "Pay close attention to comparison tables where multiple companies appear in rows — "
    "make sure each data point is matched to the correct company. "
    "Extract ONLY values explicitly stated. Do not guess or fabricate. "
    "For context_snippet fields, copy the exact line or phrase where the value appears."
)


def extract_data_from_page(page_text: str) -> dict:
    """
    Send page content to the model and return structured extracted data.
    Returns a dict with keys: page_title, companies, cost_mentions.
    """
    response = _client.chat.completions.create(
        model=config.AI_MODEL,
        max_tokens=4096,
        tools=[_EXTRACTION_TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_page_data"}},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Please extract all data points from the following page content:\n\n{page_text}",
            },
        ],
    )

    tool_calls = response.choices[0].message.tool_calls
    if tool_calls:
        return json.loads(tool_calls[0].function.arguments)

    return {"page_title": "", "companies": [], "cost_mentions": []}
