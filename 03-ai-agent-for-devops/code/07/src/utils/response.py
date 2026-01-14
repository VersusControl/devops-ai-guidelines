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
        Extracted text as string
    """
    if hasattr(response, 'content'):
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            # Handle structured content (list of content blocks)
            text_parts = []
            for block in response.content:
                if isinstance(block, dict) and 'text' in block:
                    text_parts.append(block['text'])
                elif isinstance(block, str):
                    text_parts.append(block)
            return ''.join(text_parts)
        else:
            return str(response.content)
    
    return str(response)
