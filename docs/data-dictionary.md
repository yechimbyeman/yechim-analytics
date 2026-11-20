# Data dictionary

- sources: connected platforms, groups and accounts.
- chat_members: source identities, display names, bot/internal flags.
- messages: normalized source messages and publication metadata.
- request_classifications: topic labels, intent and confidence.
- exclusions: staff and bot exclusion list by stable external ID.
- publication_metrics_snapshots: time-series snapshots of available post metrics.

Stable identity is external_user_id, not username. Usernames can change or be absent.
