# Outbound Voice Agent

Prototype for turn-based OpenAI Realtime voice interaction.

## Project Rules

- Keep the standard OpenAI API key server-side only.
- Use `gpt-realtime-2` unless Jonathan explicitly asks to test another model.
- Preserve the turn-based behavior: listen while Jonathan speaks, wait for end-of-turn, then respond.
- Prefer direct WebRTC browser APIs over adding frontend dependencies while this remains a prototype.
- Run `npm test` after changing session configuration.
