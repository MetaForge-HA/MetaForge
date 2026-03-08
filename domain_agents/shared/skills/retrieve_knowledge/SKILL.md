# retrieve_knowledge

Retrieves relevant knowledge entries from the knowledge store using semantic
similarity search.  Agents use this skill to find prior design decisions,
component datasheets, failure modes, constraints, and session context that
may inform the current task.

## Usage

Provide a natural-language query describing what you need.  Optionally filter
by `knowledge_type` and control the number of results with `limit`.

## Inputs

| Field            | Type                    | Required | Description                     |
|------------------|-------------------------|----------|---------------------------------|
| `query`          | `str`                   | yes      | Natural-language search query   |
| `knowledge_type` | `KnowledgeType \| None` | no       | Filter by knowledge category    |
| `limit`          | `int`                   | no       | Max results (default 5)         |

## Outputs

| Field         | Type                   | Description                         |
|---------------|------------------------|-------------------------------------|
| `results`     | `list[KnowledgeResult]`| Ranked list of matching entries     |
| `query`       | `str`                  | Echo of the original query          |
| `total_found` | `int`                  | Number of results returned          |
