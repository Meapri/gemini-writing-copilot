# Gemini Web Minimal Notice

This directory contains a minimal Gemini Web text-generation client adapted from:

- Repository: `https://github.com/Sophomoresty/gemini-web2api`
- Commit: `c1c2d1f071e491722422f352d99b718faa08f29d`
- License: MIT

Only the parts needed for local writing calls were retained:

- Gemini Web `StreamGenerate` payload construction
- model and thinking-depth mapping
- cookie loading and `SAPISIDHASH`
- response text extraction
- retry, timeout, and proxy-aware HTTP requests

The following `gemini-web2api` features were intentionally not vendored:

- HTTP server
- OpenAI-compatible API endpoints
- MCP integration
- tool calling
- multimodal upload
- Docker and deployment files

This plugin also adapts two local-integration patterns from:

- Repository: `https://github.com/Meapri/hermes-google-antigravity-plugin`
- Commit inspected: `5afa7fd8142225422a1adc54287e7be722eb48e8`

The adopted parts are intentionally small and plugin-local:

- private atomic JSON credential writes
- Antigravity CLI login/delegation shape using `agy --print`
- Antigravity CLI token-path awareness at
  `~/.gemini/antigravity-cli/antigravity-oauth-token`
- Antigravity-style Gemini model label aliases such as
  `google/gemini-3.1-pro-high` and `gemini-3.5-flash-low`

MIT License text from the upstream project:

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
