"""
Response formatting utilities
"""


def extract_response_text(response) -> str:
    """
    Extract text content from various response formats.
    
    LLM responses can come in different formats:
    - Plain strings
    - Objects with .content attribute
    - Structured content with multiple blocks
    
    Args:
        response: Response from LLM
    
    Returns:
        Extracted text as string (never empty)
    """
    text = ""
    
    if hasattr(response, 'content'):
        content = response.content
        
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Handle structured content (list of content blocks)
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    # Handle {'type': 'text', 'text': '...'} format
                    if 'text' in block:
                        text_parts.append(block['text'])
                elif isinstance(block, str):
                    text_parts.append(block)
            text = '\n'.join(text_parts)
    else:
        text = str(response)
    
    return text.strip()
