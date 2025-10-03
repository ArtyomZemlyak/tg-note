"""
Agent Prompts Configuration
Centralized configuration for all agent prompts and instructions
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Agent Default Instructions
# ═══════════════════════════════════════════════════════════════════════════════

QWEN_CODE_AGENT_INSTRUCTION = """You are an autonomous knowledge base agent.
Your task is to analyze content, extract key information, and save it to the knowledge base.

Process:
1. Analyze the provided content
2. Create a TODO plan for processing
3. Execute the plan using available tools
4. Structure the information appropriately
5. Generate markdown content for the knowledge base

Available tools:
- web_search: Search the web for additional context
- git_command: Execute git commands
- github_api: Interact with GitHub API
- shell_command: Execute shell commands (use cautiously)
- file_create: Create a new file
- file_edit: Edit an existing file
- file_delete: Delete a file
- file_move: Move/rename a file
- folder_create: Create a new folder
- folder_delete: Delete a folder (with contents)
- folder_move: Move/rename a folder

File and Folder Operations:
- You can create, edit, delete, and move multiple files
- You can create, delete, and move folders
- Always ensure proper file paths and handle errors gracefully

Always work autonomously without asking for clarification.
"""

QWEN_CODE_CLI_AGENT_INSTRUCTION = """You are an autonomous knowledge base agent.
Your task is to analyze content, extract key information, and create structured notes.

Process:
1. Analyze the provided content thoroughly
2. Create a TODO plan for processing (use clear markdown checklist)
3. Execute the plan step by step
4. Extract key topics, entities, and relationships
5. Structure the information with proper hierarchy
6. Generate well-formatted markdown content

Available Operations:
- File Management: Create, edit, delete, and move multiple files
- Folder Management: Create, delete, and move folders
- Content Processing: Analyze, structure, and format content
- Knowledge Base: Organize information in a logical hierarchy

Guidelines:
- Work autonomously without asking questions
- Be thorough and extract all important information
- Categorize content appropriately (AI, tech, science, etc.)
- Generate clear, concise summaries
- Include relevant metadata and tags
- Use file and folder operations when needed to organize content
"""

STUB_AGENT_INSTRUCTION = """You are a test agent for development purposes.
You simulate agent behavior without calling external services.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Templates for Content Processing
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_PROCESSING_PROMPT_TEMPLATE = """
{instruction}

# Input Content

## Text Content
{text}

{urls_section}

# Task

1. Create a TODO checklist for processing this content
2. Analyze the content and extract key information
3. Determine the category (ai, tech, biology, physics, science, business, general)
4. Extract relevant tags (3-5 keywords)
5. Generate a structured markdown document with:
   - Title (clear and descriptive)
   - Metadata section (category, tags)
   - Summary (2-3 sentences)
   - Main content (well-structured)
   - Links section (if URLs present)
   - Key takeaways

Format your response as valid markdown. Start with a clear title (# Title).
Include a metadata section in the format:
```metadata
category: <category>
tags: tag1, tag2, tag3
```

Work autonomously and provide complete output without asking questions.
"""

URLS_SECTION_TEMPLATE = """
## URLs
{url_list}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Category Detection Keywords
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS = {
    "ai": [
        "ai", "artificial intelligence", "machine learning", "neural network",
        "deep learning", "llm", "gpt", "transformer", "model", "training",
        "inference", "nlp", "natural language", "computer vision", "reinforcement learning"
    ],
    "biology": [
        "biology", "gene", "dna", "protein", "cell", "organism",
        "evolution", "genetics", "molecular", "enzyme", "chromosome",
        "rna", "mutation", "species", "ecology"
    ],
    "physics": [
        "physics", "quantum", "particle", "relativity", "energy",
        "force", "matter", "mechanics", "thermodynamics", "electromagnetic",
        "atom", "photon", "wave", "field"
    ],
    "tech": [
        "programming", "code", "software", "development", "python",
        "javascript", "api", "database", "algorithm", "framework",
        "library", "backend", "frontend", "devops", "cloud"
    ],
    "business": [
        "business", "market", "economy", "finance", "investment",
        "strategy", "management", "startup", "revenue", "profit",
        "customer", "sales", "marketing", "entrepreneur"
    ],
    "science": [
        "science", "research", "experiment", "study", "analysis",
        "hypothesis", "theory", "method", "data", "observation",
        "measurement", "discovery", "phenomenon"
    ],
}

DEFAULT_CATEGORY = "general"


# ═══════════════════════════════════════════════════════════════════════════════
# Stop Words for Keyword Extraction
# ═══════════════════════════════════════════════════════════════════════════════

STOP_WORDS = {
    # Articles
    "the", "a", "an",
    
    # Conjunctions
    "and", "or", "but", "nor", "so", "yet",
    
    # Prepositions
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "about", "against", "between", "through", "during", "before",
    "after", "above", "below", "under", "over",
    
    # Pronouns
    "i", "you", "he", "she", "it", "we", "they", "them", "their",
    "this", "that", "these", "those", "who", "what", "which", "where",
    "when", "why", "how",
    
    # Verbs
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "will", "would", "should", "could", "can", "may", "might", "must", "shall",
    
    # Other common words
    "not", "no", "yes", "all", "any", "some", "many", "much",
    "more", "most", "less", "least", "few", "several", "each", "every",
    "both", "either", "neither", "other", "another", "such", "own",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Markdown Generation Settings
# ═══════════════════════════════════════════════════════════════════════════════

# Default sections in generated markdown
DEFAULT_MARKDOWN_SECTIONS = [
    "Metadata",
    "Summary", 
    "Content",
    "Links",
    "Additional Context",
    "Keywords",
]

# Maximum lengths for various fields
MAX_TITLE_LENGTH = 60
MAX_SUMMARY_LENGTH = 200
MAX_KEYWORD_COUNT = 10
MAX_TAG_COUNT = 5

# Minimum word length for keyword extraction
MIN_KEYWORD_LENGTH = 3


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Safety Settings
# ═══════════════════════════════════════════════════════════════════════════════

# Safe git commands (read-only operations)
SAFE_GIT_COMMANDS = [
    "status",
    "log",
    "diff",
    "branch",
    "remote",
    "show",
]

# Dangerous shell command patterns to block
DANGEROUS_SHELL_PATTERNS = [
    "rm -rf",
    "rm -f",
    "> /dev",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",  # Fork bomb
    "chmod -R",
    "chown -R",
    "sudo",
    "su -",
    "wget",
    "curl",
]
