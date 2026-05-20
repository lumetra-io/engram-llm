# llm-engram

Durable, explainable long-term memory for [Simon Willison's `llm` CLI](https://llm.datasette.io), powered by [Engram](https://lumetra.io) (Lumetra).

`llm-engram` registers six tools that let any model running under `llm` store and recall facts across sessions, with semantic + knowledge-graph retrieval handled server-side.

## Install

```bash
llm install llm-engram
```

(or, from a checkout: `llm install -e .`)

## Configure

Get an API key at <https://lumetra.io>, then export it:

```bash
export LLM_ENGRAM_API_KEY=eng_live_...
# Optional: pin a default bucket so you don't have to repeat it
export LLM_ENGRAM_DEFAULT_BUCKET=my-project
# Optional: self-hosted Engram
export LLM_ENGRAM_API_BASE=https://engram.internal.example.com
```

`ENGRAM_API_KEY` is also accepted for parity with other Engram clients; `LLM_ENGRAM_API_KEY` wins if both are set.

## Tools

| Tool | What it does |
|---|---|
| `engram_store_memory` | Save an atomic fact/preference/decision. Args: `content`, optional `bucket`. |
| `engram_query_memory` | Ask a natural-language question against memory. Args: `question`, optional `bucket`. |
| `engram_list_memories` | List raw memories in a bucket. Args: optional `bucket`, `limit`, `offset`. |
| `engram_list_buckets` | List buckets visible to this API key. Args: optional `limit`, `offset`. |
| `engram_delete_memory` | Delete one memory by `memory_id`. Args: `memory_id`, optional `bucket`. |
| `engram_clear_memories` | Wipe a bucket. Destructive. Args: optional `bucket`. |

## Usage

List the tools:

```bash
llm tools
```

One-shot:

```bash
llm -T engram_store_memory "Remember: I prefer pytest over unittest."
llm -T engram_query_memory "What testing framework do I prefer?"
```

Chat with memory wired in:

```bash
llm chat -T engram_store_memory -T engram_query_memory \
         -T engram_list_memories -T engram_list_buckets
```

Per-call bucket override:

```bash
llm -T engram_store_memory \
    "Q2 OKR: ship v2 of the ingest pipeline" \
    --tools-arg engram_store_memory bucket=work
```

## Self-hosting

Point `LLM_ENGRAM_API_BASE` at any Engram-compatible REST endpoint. The plugin uses only the documented `/v1/...` routes.

## Privacy

See [PRIVACY.md](./PRIVACY.md).

## License

MIT — see [LICENSE](./LICENSE).
