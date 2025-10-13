# Qwen Code CLI agent examples with multiple files

## Example 1: Article about a new model

### Incoming message

```
User in Telegram:

Forwarded article:
Claude 3.5 Sonnet - a new model from Anthropic with improved coding
and reasoning. The model outperforms GPT-4 in programming benchmarks
and shows great results in math.

Link: https://www.anthropic.com/news/claude-3-5-sonnet
```

### What the agent does

#### Step 1: Analysis

```
Qwen-code agent analyzes:
- Type: article about a model
- Topics:
  1. Claude 3.5 Sonnet model
  2. Anthropic company
  3. Coding capabilities
  4. Reasoning capabilities
  5. Comparison with GPT-4
```

#### Step 2: Plan (TODO)

```markdown
Agent creates a plan:

- [x] Language: RUSSIAN
- [x] Detect source type: model article
- [x] Web search: find info about Anthropic
- [x] Web search: find info about Claude 3.5
- [x] Identify topics: 4 topics
- [x] Create folders: ai/models, companies, ai/capabilities
- [x] Create file: ai/models/claude-3-5-sonnet.md
- [x] Create file: companies/anthropic.md
- [x] Create file: ai/capabilities/coding.md
- [x] Create file: ai/capabilities/reasoning.md
- [x] Add cross-links between files
```

#### Step 3: Execution

```bash
# qwen CLI performs:

1. folder_create ai/models
2. folder_create companies
3. folder_create ai/capabilities

4. file_create ai/models/claude-3-5-sonnet.md
5. file_create companies/anthropic.md
6. file_create ai/capabilities/coding.md
7. file_create ai/capabilities/reasoning.md

8. file_edit ai/models/claude-3-5-sonnet.md  # Add links
9. file_edit companies/anthropic.md           # Add links
10. file_edit ai/capabilities/coding.md       # Add links
11. file_edit ai/capabilities/reasoning.md    # Add links
```

### Created files

#### `ai/models/claude-3-5-sonnet.md`

```markdown
# Claude 3.5 Sonnet

## Description
Claude 3.5 Sonnet is a language model from Anthropic, released in 2024.
It represents an improved version of the Claude 3 series with a focus
on programming and logical reasoning.

## Main information

### Technical specs
- **Developer**: [[companies/anthropic.md|Anthropic]]
- **Family**: Claude 3.x
- **Version**: 3.5 Sonnet
- **Release year**: 2024

### Capabilities

#### Programming
- Excellent code generation
- Understanding complex algorithms
- Refactoring and optimization
- Debugging and code review

See also: [[ai/capabilities/coding.md|Coding capabilities of AI]]

#### Reasoning
- Improved logical reasoning
- Solving math problems
- Multi-step reasoning

See also: [[ai/capabilities/reasoning.md|Reasoning in AI models]]

## Key concepts
- **Constitutional AI**: Safer behavior through principles
- **Extended context**: Support for long dialogues
- **Reasoning**: Advanced reasoning capabilities

## Comparison with competitors

### vs GPT-4
- ✅ Better at programming (benchmarks)
- ✅ Better at math
- ≈ Comparable in general tasks

## Use cases
- Software development assistance
- Code review and optimization
- Learning programming
- Solving complex math problems

## Sources
- https://www.anthropic.com/news/claude-3-5-sonnet
- https://www.anthropic.com/claude
```

#### `companies/anthropic.md`

```markdown
# Anthropic

## Description
Anthropic is an AI company founded in 2021 by former OpenAI employees.
Specializes in safe and reliable AI.

## Main information

### History
- **Founded**: 2021
- **Founders**: Dario Amodei, Daniela Amodei and other ex-OpenAI
- **HQ**: San Francisco, USA

### Mission
Build reliable, interpretable, and steerable AI systems.

### Key approaches
- **Constitutional AI**: Principle-based learning
- **Safety-first**: Safety as priority
- **Alignment research**: AI alignment research

## Products

### Claude (model family)
- Claude 1 (2022)
- Claude 2 (2023)
- Claude 3 (Opus, Sonnet, Haiku) (2024)
- [[ai/models/claude-3-5-sonnet.md|Claude 3.5 Sonnet]] (2024)

### API
- Claude API for developers
- Integration with applications

## Investments
- Google (2023)
- Spark Capital
- Total: $1.5B+

## Related topics
- [[ai/models/claude-3-5-sonnet.md]] — Latest model
- [[ai/safety/constitutional-ai.md]] — Safety approach
- [[companies/openai.md]] — Competitor

## Sources
- https://www.anthropic.com
- https://www.anthropic.com/company
```

#### `ai/capabilities/coding.md`

```markdown
# Coding capabilities of AI models

## Description
Overview of modern AI models' capabilities in programming,
code generation and developer assistance.

## Main information

### Task types
1. **Code generation**
   - Writing functions from description
   - Creating modules
   - Test generation

2. **Code understanding**
   - Explaining code
   - Finding bugs
   - Code review

3. **Refactoring**
   - Optimization
   - Improving readability
   - Best practices

4. **Debugging**
   - Finding errors
   - Proposing fixes
   - Explaining problems

### Benchmarks
- **HumanEval**: Code generation
- **MBPP**: Mostly Basic Python Problems
- **CodeContests**: Competitive programming

## Key models

### Specialized
- Codex (OpenAI)
- CodeLlama (Meta)
- StarCoder (BigCode)

### General with strong coding
- [[ai/models/claude-3-5-sonnet.md|Claude 3.5 Sonnet]] — current leader
- GPT-4
- Gemini 1.5

## Use cases

### 1. Code generation
```python
# Task: "Create a quicksort function"

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
```

### 2. Bug finding

The model can find bugs and suggest fixes.

### 3. Explaining code

Step-by-step code explanation.

## Limitations

- Not always optimal solutions
- May contain subtle bugs
- Requires human review

## Related topics

- [[ai/models/claude-3-5-sonnet.md]] — Strong coding model
- [[ai/capabilities/reasoning.md]] — Reasoning for coding
- [[tech/tools/github-copilot.md]] — Coding assistant

## Sources

- <https://paperswithcode.com/task/code-generation>
- <https://huggingface.co/spaces/bigcode/bigcode-models-leaderboard>
```

#### `ai/capabilities/reasoning.md`

```markdown
# Reasoning in AI models

## Description
AI models' ability to logical reasoning and solving
complex problems requiring multi-step thinking.

## Main information

### Types of reasoning
1. **Deductive reasoning**
   - From general to specific
   - Logical inferences

2. **Inductive reasoning**
   - From specific to general
   - Generalizations and patterns

3. **Abductive reasoning**
   - Best explanation search
   - Hypotheses

4. **Analogical reasoning**
   - Comparing situations
   - Applying knowledge

### Mathematical reasoning
- Solving equations
- Proving theorems
- Word problems
- Geometry

### Chain-of-Thought (CoT)
Prompting technique to improve reasoning:
- Step-by-step reasoning
- Explicit thoughts
- Intermediate conclusions

## Models with strong reasoning

### Current leaders
- [[ai/models/claude-3-5-sonnet.md|Claude 3.5 Sonnet]]
- GPT-4
- Gemini 1.5 Pro

### Specialized
- AlphaGeometry (math)
- MinervaLM (STEM)

## Benchmarks
- **GSM8K**: Grade school math
- **MATH**: Math problems
- **ARC**: Abstract reasoning
- **BigBench**: Comprehensive test

## Examples

### Math problem
```
Problem: John has 5 apples. He gave 2 apples to Mary.
Mary gave half of her apples to Bob. How many apples does Bob have?

Reasoning:

1. John had 5 apples
2. He gave 2 to Mary → Mary has 2 apples
3. Mary gave half to Bob → 2/2 = 1
4. Bob has 1 apple

Answer: 1 apple
```

### Logical task
The model can solve logic problems with step-by-step reasoning.

## Improving reasoning

### Prompting techniques
- Chain-of-Thought
- Self-consistency
- Tree of Thoughts
- ReAct (Reasoning + Acting)

### Fine-tuning
- On datasets with reasoning
- Synthetic data generation

## Related topics

- [[ai/models/claude-3-5-sonnet.md]] — Model with strong reasoning
- [[ai/prompting/chain-of-thought.md]] — CoT technique
- [[ai/capabilities/coding.md]] — Reasoning for programming

## Sources
- https://arxiv.org/abs/2201.11903 (Chain-of-Thought paper)
- https://paperswithcode.com/task/mathematical-reasoning
```

### Result for the user

```
Telegram bot →  To the user:

✅ Information added to Knowledge Base!

Created files:
📄 ai/models/claude-3-5-sonnet.md
📄 companies/anthropic.md
📄 ai/capabilities/coding.md
📄 ai/capabilities/reasoning.md

Topics:
🏷 AI models
🏷 Companies
🏷 Programming
🏷 Logical reasoning

Files are cross-linked for easy navigation.
```

## Example 2: Technical note

### Input

```
User:

Note: Tried a new approach to RAG — instead of simple
vector search, first use LLM to generate queries,
then hybrid search (vector + BM25), and then re-ranking.
Works much better!

Can be combined with query expansion and HyDE.
```

### Agent output

```
Created files:

1. ai/rag/advanced-retrieval.md
   - Advanced retrieval techniques
   - Hybrid search
   - Re-ranking

2. ai/rag/query-optimization.md
   - Query generation via LLM
   - Query expansion
   - HyDE (Hypothetical Document Embeddings)

3. tech/search/hybrid-search.md
   - Vector search
   - BM25
   - Combining approaches

4. tech/search/reranking.md
   - Re-ranking methods
   - Models for re-ranking
   - Best practices

Files are cross-referenced.
```

## Example 3: News from multiple sources

### Input

```
User (forwards several messages):

1) Meta released Llama 3.1 with 405B parameters
2) Supports 128K context window
3) Open source under Llama license
4) Beats GPT-4 on many benchmarks
```

### Agent creates

```
1. companies/meta.md
   - About Meta
   - AI research
   - Open source policy

2. ai/models/llama-3-1.md
   - Llama 3.1 details
   - 405B version
   - Benchmarks

3. ai/concepts/model-sizes.md
   - Model sizes
   - 405B parameters
   - Scaling laws

4. ai/licensing/open-source-models.md
   - Open source in AI
   - Llama license
   - License comparison

5. ai/context/long-context-models.md
   - Long context
   - 128K tokens
   - Use cases
```

---

These examples show how the qwen-code CLI agent automatically:

- Analyzes information
- Splits by topics
- Creates structure
- Populates files
- Links everything together
