# External technical references

Concise local records of external APIs, libraries and CLIs this project depends on, created with:

```
harness new api-reference "Service — endpoint"
harness new library-reference "Library — topic"
harness new cli-reference "Tool — commands"
```

Organise by technology and topic (one directory per technology is fine). Each reference records the source URL,
the version consulted, the verification date, sanitised request/response shapes and the implementation that uses it.
Never store tokens, cookies, real user data or sensitive response bodies. Mark a reference `needs-revalidation`
when behaviour drifts. Check here before searching the internet.
