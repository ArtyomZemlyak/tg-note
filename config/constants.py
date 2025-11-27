"""
Constants for tg-note project

This module contains constants used across the project that are not related to prompts.
Prompt-related functionality has been moved to direct promptic.render() calls.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# Category Detection Keywords
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS = {
    "ai": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "neural network",
        "deep learning",
        "llm",
        "gpt",
        "transformer",
        "model",
        "training",
        "inference",
        "nlp",
        "natural language",
        "computer vision",
        "reinforcement learning",
    ],
    "biology": [
        "biology",
        "gene",
        "dna",
        "protein",
        "cell",
        "organism",
        "evolution",
        "genetics",
        "molecular",
        "enzyme",
        "chromosome",
        "rna",
        "mutation",
        "species",
        "ecology",
    ],
    "physics": [
        "physics",
        "quantum",
        "particle",
        "relativity",
        "energy",
        "force",
        "matter",
        "mechanics",
        "thermodynamics",
        "electromagnetic",
        "atom",
        "photon",
        "wave",
        "field",
    ],
    "tech": [
        "programming",
        "code",
        "software",
        "development",
        "python",
        "javascript",
        "api",
        "database",
        "algorithm",
        "framework",
        "library",
        "backend",
        "frontend",
        "devops",
        "cloud",
    ],
    "business": [
        "business",
        "market",
        "economy",
        "finance",
        "investment",
        "strategy",
        "management",
        "startup",
        "revenue",
        "profit",
        "customer",
        "sales",
        "marketing",
        "entrepreneur",
    ],
    "science": [
        "science",
        "research",
        "experiment",
        "study",
        "analysis",
        "hypothesis",
        "theory",
        "method",
        "data",
        "observation",
        "measurement",
        "discovery",
        "phenomenon",
    ],
}

DEFAULT_CATEGORY = "general"

# ═══════════════════════════════════════════════════════════════════════════════
# Stop Words for Keyword Extraction
# ═══════════════════════════════════════════════════════════════════════════════

STOP_WORDS = {
    # Articles
    "the",
    "a",
    "an",
    # Conjunctions
    "and",
    "or",
    "but",
    "nor",
    "so",
    "yet",
    # Prepositions
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "into",
    "about",
    "against",
    "between",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "under",
    "over",
    # Pronouns
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "them",
    "their",
    "this",
    "that",
    "these",
    "those",
    "who",
    "what",
    "which",
    "where",
    "when",
    "why",
    "how",
    # Verbs
    "is",
    "am",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "will",
    "would",
    "should",
    "could",
    "can",
    "may",
    "might",
    "must",
    "shall",
    # Other common words
    "not",
    "no",
    "yes",
    "all",
    "any",
    "some",
    "many",
    "much",
    "more",
    "most",
    "less",
    "least",
    "few",
    "several",
    "each",
    "every",
    "both",
    "either",
    "neither",
    "other",
    "another",
    "such",
    "own",
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
