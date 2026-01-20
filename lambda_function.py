import json
import boto3
import os
import re

bedrock = boto3.client("bedrock-runtime")

# --- NEW: Forbidden Word List ---
FORBIDDEN_RETURN_WORD = ["prompt", "assistant", "json"]

# =========================
# Absolute / Definitive claims
# =========================
FORBIDDEN_ABSOLUTE = [
    "100%",
    "100 percent",
    "percent",
    "definitely",
    "definitive",
    "absolute",
    "absolutely",
    "totally",
    "completely"
]

# =========================
# Quality / branding claims
# =========================
FORBIDDEN_QUALITY = [
    "brand",
    "high quality",
    "top quality",
    "premium",
    "new",
    "perfect",
    "perfectly"
]

# =========================
# Promotion / sales language
# =========================
FORBIDDEN_PROMOTIONAL = [
    "best-selling",
    "best selling",
    "bestselling",
    "top-selling",
    "top selling",
    "topselling",
    "promotion",
    "promotional"
]

# =========================
# Material / technology (ABS 特例你已在逻辑里处理)
# =========================
FORBIDDEN_MATERIAL = [
    "led",
    "uv",
    "ultraviolet",
    "hid",
    "laser",
    "plexiglas"
]

# =========================
# Smell / gas / pollution
# =========================
FORBIDDEN_SMELL = [
    "smell",
    "odor",
    "odour",
    "gas",
    "pollution",
    "fresh",
    "dirty",
    "stinky"
]

# =========================
# Insects (图片强调：任何“虫”都不允许)
# =========================
FORBIDDEN_INSECT = [
    "insect",
    "insects",
    "bug",
    "bugs",
    "worm",
    "worms",
    "ant",
    "ants",
    "cockroach",
    "cockroaches",
    "mosquito",
    "mosquitoes",
    "fly",
    "flies"
]

# =========================
# Review / inducement / service
# =========================
FORBIDDEN_GUIDING = [
    "good review",
    "bad review",
    "free",
    "service",
    "duty",
    "tax"
]

# =========================
# Logistics / shipping
# =========================
FORBIDDEN_LOGISTICS = [
    "delivery time",
    "free shipping",
    "fast shipping",
    "express delivery",
    "express shipping"
]

# =========================
# URLs (你已有正则清理，这里兜底)
# =========================
FORBIDDEN_URL = [
    "http://",
    "https://",
    "www."
]

# =========================
# Origin / originality (图片要求直接删除)
# =========================
FORBIDDEN_ORIGIN = [
    "original",
    "origin",
    "made in china",
    "mainland china",
    "cn",
    "OEM"
]

# =========================
# External certification
# =========================
FORBIDDEN_CERTIFICATION = [
    "external testing certification"
]

# =========================
# ALL FORBIDDEN WORDS
# =========================
FORBIDDEN_WORDS_ALL = (
    FORBIDDEN_ABSOLUTE +
    FORBIDDEN_QUALITY +
    FORBIDDEN_PROMOTIONAL +
    FORBIDDEN_MATERIAL +
    FORBIDDEN_SMELL +
    FORBIDDEN_INSECT +
    FORBIDDEN_GUIDING +
    FORBIDDEN_LOGISTICS +
    FORBIDDEN_URL +
    FORBIDDEN_ORIGIN +
    FORBIDDEN_CERTIFICATION
)


# --- Function to read the prompt from the file ---
def load_system_prompt():
    """Reads the SYSTEM_PROMPT content from the local file."""
    file_path = os.path.join(os.path.dirname(__file__), 'system_prompt.txt')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error loading system prompt: {e}")
        return "You are a helpful assistant." 

SYSTEM_PROMPT = load_system_prompt()
# ----------------------------------------------------


TEMPLATE = """产品标题：
{title}

产品要点：
{title}
{bullet_point}

产品描述：
{title}
{description}

亚马逊平均价格：
{amazon_avg_price}

亚马逊最低价格：
{amazon_min_price}

亚马逊最低价格产品：
{amazon_min_price_product}

亚马逊最低价格产品链接：
{amazon_min_price_product_url}

速卖通建议价格：
{ali_express_rec_price}
"""

# --- Special Pattern Removal Functions ---
def remove_special_patterns(text):
    """
    Remove special patterns that are forbidden:
    - URLs/website links
    - Single letter M surrounded by spaces (e.g., " M ", "【 M 】")
    - Mercedes Benz (keep only "奔驰Benz" if present)
    - Volkswagen (replace with VW, or delete if "Volkswagen VW" appears)
    - Origin information like "Origin: Mainland China CN"
    - Competitor disparaging text
    """
    if not text:
        return text
    
    # Remove URLs (http://, https://, www.)
    text = re.sub(r'https?://[^\s]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'www\.[^\s]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}[^\s]*', '', text)  # Generic domain patterns
    
    # Remove single letter M surrounded by spaces or brackets
    # Match: " M ", "【 M 】", "（ M ）", etc.
    text = re.sub(r'[【（(\[]\s*M\s*[】）)\]]', '', text)
    text = re.sub(r'\s+M\s+', ' ', text)  # Space-surrounded M
    text = re.sub(r'^\s*M\s+', '', text)  # M at start
    text = re.sub(r'\s+M\s*$', '', text)  # M at end
    
    # Handle Mercedes Benz - delete all occurrences, but keep "奔驰Benz" if it exists separately
    # Remove "Mercedes Benz", "Mercedes", "梅赛德斯Mercedes" but keep standalone "奔驰Benz"
    text = re.sub(r'mercedes\s*benz', '', text, flags=re.IGNORECASE)
    text = re.sub(r'mercedes', '', text, flags=re.IGNORECASE)
    text = re.sub(r'梅赛德斯\s*mercedes', '', text, flags=re.IGNORECASE)
    
    # Handle Volkswagen - replace with VW, or delete if "Volkswagen VW" appears together
    if re.search(r'volkswagen\s+vw', text, re.IGNORECASE):
        text = re.sub(r'volkswagen\s+', '', text, flags=re.IGNORECASE)
    else:
        text = re.sub(r'\bvolkswagen\b', 'VW', text, flags=re.IGNORECASE)
    
    # Remove origin information patterns
    text = re.sub(r'origin\s*:\s*mainland\s*china\s*cn', '', text, flags=re.IGNORECASE)
    text = re.sub(r'origin\s*:\s*mainland\s*china', '', text, flags=re.IGNORECASE)
    text = re.sub(r'原产地\s*:\s*mainland\s*china\s*cn', '', text, flags=re.IGNORECASE)
    
    # Remove "Original" standalone word
    text = re.sub(r'\boriginal\b', '', text, flags=re.IGNORECASE)
    
    # Remove competitor disparaging patterns (simplified - look for common patterns)
    # Patterns like "better than other stores", "superior to other brands", etc.
    disparaging_patterns = [
        r'superior\s+to\s+other',
        r'better\s+than\s+other',
        r'quality\s+is\s+superior\s+to\s+other',
        r'better\s+quality\s+than\s+other'
    ]
    for pattern in disparaging_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Clean up multiple spaces but preserve newlines
    # Replace multiple spaces/tabs (but not newlines) with single space
    text = re.sub(r'[ \t]+', ' ', text)  # Only replace spaces and tabs, not newlines
    # Clean up multiple consecutive newlines (keep single newline)
    text = re.sub(r'\n\s*\n+', '\n', text)  # Multiple newlines -> single newline
    # Clean up spaces around newlines
    text = re.sub(r' +\n', '\n', text)  # Remove spaces before newline
    text = re.sub(r'\n +', '\n', text)  # Remove spaces after newline
    text = text.strip()
    
    return text


def filter_forbidden_words(text, field_type="description"):
    """
    Filter forbidden words from text based on field type.
    
    Args:
        text: The text to filter
        field_type: Either "bullet_point" or "description"
    
    Returns:
        Filtered text with forbidden words removed
    """
    if text is None:
        return None
    if not text:
        return text
    
    # First, apply special pattern removal
    text = remove_special_patterns(text)
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    original_text = text
    words_to_remove = []
    
    # Check all forbidden words
    for forbidden_word in FORBIDDEN_WORDS_ALL:
        # Case-insensitive search
        if forbidden_word.lower() in text_lower:
            words_to_remove.append(forbidden_word)
    
    # Special rule: ABS is forbidden in bullet_point but allowed in description
    if field_type == "bullet_point":
        if "abs" in text_lower:
            # Remove ABS from bullet_point
            text = re.sub(r'\babs\b', '', text, flags=re.IGNORECASE)
    
    # Remove forbidden words (case-insensitive)
    for word in words_to_remove:
        # Use word boundaries to avoid partial matches where appropriate
        # For multi-word phrases, use simple replacement
        if ' ' in word:
            # Multi-word phrase - replace directly
            pattern = re.escape(word)
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        else:
            # Single word - use word boundaries for better matching
            pattern = r'\b' + re.escape(word) + r'\b'
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Clean up multiple spaces but preserve newlines
    # Replace multiple spaces (but not newlines) with single space
    text = re.sub(r'[ \t]+', ' ', text)  # Only replace spaces and tabs, not newlines
    # Clean up multiple consecutive newlines (keep single newline)
    text = re.sub(r'\n\s*\n+', '\n', text)  # Multiple newlines -> single newline
    # Clean up spaces around newlines
    text = re.sub(r' +\n', '\n', text)  # Remove spaces before newline
    text = re.sub(r'\n +', '\n', text)  # Remove spaces after newline
    text = text.strip()
    
    return text


# --- NEW: Forbidden Word Check Function ---
def check_forbidden_words(structured_data, forbidden_list):
    """
    Checks if any word in the forbidden list exists in the title, bullet_point, or description fields.
    Returns the first forbidden word found, or None if clean.
    """
    fields_to_check = [
        structured_data.get("title", ""),
        structured_data.get("bullet_point", ""),
        structured_data.get("description", "")
    ]

    # Combine all text and split into words for a case-insensitive check
    full_text = " ".join(fields_to_check).lower()
    
    for word in forbidden_list:
        # Check if the forbidden word exists as a whole word or substring
        # Using 'in' is simpler and covers most common scenarios like "assistant's" or "json-like"
        if word.lower() in full_text:
            return word

    return None
# ----------------------------------------------------


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': ''
        }

    try:
        body = json.loads(event.get("body", "{}"))
        user_input = body.get("input_text", "").strip()
    except Exception:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid body"})}

    if not user_input:
        return {"statusCode": 400, "body": json.dumps({"error": "input_text is required"})}

    messages = [
    {"role": "user", "content": [{"type": "text", "text": SYSTEM_PROMPT + "\n" + user_input}]}
    ]

    response = bedrock.invoke_model(
        modelId="arn:aws:bedrock:us-west-2:443042673085:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": 2000
            })
        )

    model_output = json.loads(response["body"].read())
    output_text = model_output.get("content", [{}])[0].get("text", "")

    if output_text.startswith("```"):
        output_text = "\n".join(output_text.split("\n")[1:-1])

    try:
        structured = json.loads(output_text)
    except json.JSONDecodeError:
        return {"statusCode": 500, "body": json.dumps({"error": "LLM did not return valid JSON", "raw_output": output_text})}


    # --- NEW: Forbidden Word Check Execution ---
    forbidden_word_found = check_forbidden_words(structured, FORBIDDEN_RETURN_WORD)
    if forbidden_word_found:
        return {
            "statusCode": 500,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            "body": json.dumps({
                "error": "LLM output contained a forbidden word.",
                "forbidden_word": forbidden_word_found
            })
        }
    # ---------------------------------------------

    # --- Filter forbidden words from bullet_point and description ---
    if "bullet_point" in structured:
        structured["bullet_point"] = filter_forbidden_words(
            structured["bullet_point"], 
            field_type="bullet_point"
        )
    
    if "description" in structured:
        structured["description"] = filter_forbidden_words(
            structured["description"], 
            field_type="description"
        )
    # ----------------------------------------------------------------

    # 使用模板填充
    final_text = TEMPLATE.format(
        title=structured.get("title", ""),
        bullet_point=structured.get("bullet_point", ""),
        description=structured.get("description", ""),
        amazon_avg_price=structured.get("amazon_avg_price", "N/A"),
        amazon_min_price=structured.get("amazon_min_price", "N/A"),
        amazon_min_price_product=structured.get("amazon_min_price_product", "N/A"),
        amazon_min_price_product_url=structured.get("amazon_min_price_product_url", "N/A"),
        ali_express_rec_price=structured.get("ali_express_rec_price", "N/A")
        )

    # 在最后返回时确保包含这些头
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        },
        "body": json.dumps({
            "result": final_text,
            "result_structured": structured
        })
    }

