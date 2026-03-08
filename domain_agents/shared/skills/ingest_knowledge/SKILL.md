# ingest_knowledge

Ingests new knowledge into the knowledge store.  Content is chunked (if
long), embedded via the configured embedding service, and persisted in the
knowledge store for later semantic retrieval.

## Usage

Provide the textual content, its knowledge type, and optional metadata.
The skill returns the ID of the created entry and whether embedding
succeeded.

## Inputs

| Field                | Type                | Required | Description                        |
|----------------------|---------------------|----------|------------------------------------|
| `content`            | `str`               | yes      | Text content to ingest             |
| `knowledge_type`     | `KnowledgeType`     | yes      | Category of knowledge              |
| `metadata`           | `dict`              | no       | Arbitrary metadata                 |
| `source_artifact_id` | `UUID \| None`      | no       | Source artifact in the Digital Twin |

## Outputs

| Field      | Type   | Description                                     |
|------------|--------|-------------------------------------------------|
| `entry_id` | `UUID` | ID of the newly created knowledge entry         |
| `embedded` | `bool` | Whether the content was successfully embedded   |
