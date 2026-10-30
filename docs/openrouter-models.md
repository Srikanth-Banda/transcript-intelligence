# OpenRouter candidate models (raw table)

Source: GET https://openrouter.ai/api/v1/models (420 models returned) and GET /api/v1/models/{id}/endpoints, retrieved 2026-10-29 with the project key. Prices are USD per million tokens as listed by OpenRouter (model-level; individual providers may differ, especially for open-weight models). Filtered to major families, created on or after 2026-04-01 (plus claude-haiku-4.5 for reference), excluding image/omni/:batch variants (batch variants are listed at roughly half price; they are asynchronous and not considered). Flags: S=structured_outputs, R=response_format, T=temperature, Seed=seed, as appearing in the model's supported_parameters.

**Important:** Claude 5.x and GPT-6/6.1 slugs do NOT list `temperature` in supported_parameters (reasoning models). A request with temperature=0 was accepted without error by claude-haiku-5.5, claude-sonnet-5.5, gpt-6-luna and gemini-3.8-flash on 2026-10-29, but whether the value is honoured is NOT verified. Claude slugs also list no `seed`.

| slug | created | context | in $/M | out $/M | S | R | T | Seed | reasoning | providers (endpoints API) |
|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-6.1-terra-pro | 2026-10-26 | 1,050,000 | 1 | 5 | Y | Y | - | Y | mandatory |  |
| openai/gpt-6.1-terra | 2026-10-26 | 1,050,000 | 1 | 5 | Y | Y | - | Y | optional | Azure, OpenAI |
| moonshotai/kimi-k3.1-pro | 2026-10-23 | 1,048,576 | 2 | 10 | Y | Y | - | - | optional | Moonshot AI |
| deepseek/deepseek-v4.1-flash-1017 | 2026-10-17 | 1,048,576 | 0.044 | 0.383 | Y | Y | Y | Y | optional |  |
| google/gemini-4-argon | 2026-10-13 | 1,048,576 | 2 | 10 | Y | Y | Y | Y | mandatory | Google, Google AI Studio |
| anthropic/claude-haiku-5.5 | 2026-10-07 | 1,000,000 | 0.1 | 0.5 | Y | Y | - | - | optional | Amazon Bedrock, Anthropic, Azure, Claude Platform on AWS, Google |
| mistralai/mistral-large-4-0 | 2026-10-06 | 1,048,576 | 0.7 | 2.1 | Y | Y | Y | Y | optional | Mistral |
| openai/gpt-6.1-sol-pro | 2026-09-29 | 1,050,000 | 2 | 10 | Y | Y | - | Y | mandatory |  |
| openai/gpt-6.1-sol | 2026-09-29 | 1,050,000 | 2 | 10 | Y | Y | - | Y | mandatory |  |
| anthropic/claude-sonnet-5.5 | 2026-09-28 | 1,000,000 | 2 | 10 | Y | Y | - | - | mandatory | Amazon Bedrock, Anthropic, Azure, Claude Platform on AWS, Google |
| z-ai/glm-5.3-prime | 2026-09-23 | 1,000,000 | 2.8 | 8.8 | - | Y | Y | Y | mandatory |  |
| qwen/qwen3.8-max-prime | 2026-09-23 | 1,000,000 | 4 | 12 | Y | Y | Y | Y | mandatory |  |
| openai/gpt-6-luna-pro | 2026-09-22 | 1,050,000 | 0.1 | 0.5 | Y | Y | - | Y | optional |  |
| openai/gpt-6-luna | 2026-09-22 | 1,050,000 | 0.1 | 0.5 | Y | Y | - | Y | optional | Amazon Bedrock, Azure, OpenAI |
| openai/gpt-6-sol-pro | 2026-09-22 | 1,050,000 | 2 | 10 | Y | Y | - | Y | optional |  |
| openai/gpt-6-sol | 2026-09-22 | 1,050,000 | 2 | 10 | Y | Y | - | Y | optional | Amazon Bedrock, Azure, OpenAI |
| anthropic/claude-opus-5.5 | 2026-09-22 | 1,000,000 | 4 | 20 | Y | Y | - | - | mandatory | Amazon Bedrock, Anthropic, Azure, Claude Platform on AWS, Google |
| x-ai/grok-4.7 | 2026-09-21 | 500,000 | 2 | 6 | Y | Y | Y | Y | mandatory | xAI |
| z-ai/glm-5.3-flashx | 2026-09-18 | 1,048,576 | 0.37 | 1.25 | - | Y | Y | - | mandatory |  |
| deepseek/deepseek-v4.1-flash | 2026-09-09 | 1,048,576 | 0.045 | 0.5 | Y | Y | Y | Y | optional | 32 providers |
| openai/gpt-6-astra | 2026-09-04 | 1,050,000 | 10 | 50 | Y | Y | - | Y | mandatory |  |
| openai/gpt-6-astra-pro | 2026-09-04 | 1,050,000 | 10 | 50 | Y | Y | - | Y | mandatory |  |
| qwen/qwen3.8-max-0902 | 2026-09-03 | 1,000,000 | 2 | 6 | Y | Y | Y | Y | mandatory | Alibaba |
| google/gemini-3.8-flash | 2026-09-02 | 1,048,576 | 0.75 | 3.75 | Y | Y | Y | Y | mandatory | Google, Google AI Studio |
| anthropic/claude-fable-5.1 | 2026-09-01 | 1,000,000 | 10 | 50 | Y | Y | - | - | mandatory |  |
| qwen/qwen3.8-flash | 2026-08-26 | 1,000,000 | 0.15 | 0.47 | Y | Y | Y | Y | optional | Alibaba |
| z-ai/glm-5.3-flash | 2026-08-26 | 1,048,576 | 0.15 | 0.5 | Y | Y | Y | Y | mandatory |  |
| deepseek/deepseek-v4-flash-vision-exp | 2026-08-21 | 1,048,576 | 0.216 | 0.647 | Y | Y | Y | Y | optional |  |
| z-ai/glm-5.3 | 2026-08-18 | 1,048,576 | 0.0699 | 1.4 | Y | Y | Y | Y | mandatory |  |
| qwen/qwen3.8-27b | 2026-08-14 | 1,000,000 | 0.039 | 1.25 | Y | Y | Y | Y | optional |  |
| google/gemini-3.7-flash | 2026-08-13 | 1,048,576 | 0.75 | 3.75 | Y | Y | Y | Y | mandatory |  |
| qwen/qwen3.8-2.4t-a95b | 2026-08-12 | 1,048,576 | 2 | 6 | Y | Y | Y | Y | mandatory |  |
| deepseek/deepseek-v4-pro-0813 | 2026-08-12 | 1,048,576 | 0.103 | 8 | Y | Y | Y | Y | optional |  |
| x-ai/grok-4.6 | 2026-08-12 | 500,000 | 2 | 6 | Y | Y | Y | Y | mandatory |  |
| deepseek/deepseek-v4-flash-0731 | 2026-07-30 | 1,048,576 | 0.119 | 0.238 | Y | Y | Y | Y | optional |  |
| qwen/qwen3.7-flash | 2026-07-27 | 1,000,000 | 0.03 | 0.13 | - | Y | Y | Y | optional |  |
| anthropic/claude-opus-5 | 2026-07-24 | 1,000,000 | 5 | 25 | Y | Y | - | - | optional |  |
| google/gemini-3.6-flash | 2026-07-21 | 1,048,576 | 0.75 | 3.75 | Y | Y | Y | Y | mandatory |  |
| google/gemini-3.5-flash-lite | 2026-07-21 | 1,048,576 | 0.3 | 2.5 | Y | Y | Y | Y | mandatory | Google, Google AI Studio |
| moonshotai/kimi-k3 | 2026-07-16 | 1,048,576 | 0.239 | 10.8 | Y | Y | Y | Y | optional |  |
| openai/gpt-5.6-luna-pro | 2026-07-09 | 1,050,000 | 0.2 | 1.2 | Y | Y | - | Y | optional |  |
| openai/gpt-5.6-luna | 2026-07-09 | 1,050,000 | 0.2 | 1.2 | Y | Y | - | Y | optional |  |
| openai/gpt-5.6-terra-pro | 2026-07-09 | 1,050,000 | 2 | 12 | Y | Y | - | Y | optional |  |
| openai/gpt-5.6-terra | 2026-07-09 | 1,050,000 | 2 | 12 | Y | Y | - | Y | optional |  |
| openai/gpt-5.6-sol-pro | 2026-07-09 | 1,050,000 | 4 | 20 | Y | Y | - | Y | optional |  |
| openai/gpt-5.6-sol | 2026-07-09 | 1,050,000 | 4 | 20 | Y | Y | - | Y | optional |  |
| x-ai/grok-4.5 | 2026-07-08 | 500,000 | 2 | 6 | Y | Y | Y | Y | mandatory |  |
| anthropic/claude-sonnet-5 | 2026-06-30 | 1,000,000 | 2 | 10 | Y | Y | - | - | optional |  |
| z-ai/glm-5.2 | 2026-06-16 | 1,048,576 | 0.006 | 8 | Y | Y | Y | Y | optional |  |
| moonshotai/kimi-k2.7-code | 2026-06-12 | 262,144 | 0.56 | 3.1 | Y | Y | Y | Y | mandatory |  |
| anthropic/claude-fable-5 | 2026-06-09 | 1,000,000 | 10 | 50 | Y | Y | - | - | mandatory |  |
| qwen/qwen3.7-plus | 2026-06-03 | 1,000,000 | 0.32 | 1.28 | Y | Y | Y | Y | optional |  |
| anthropic/claude-opus-4.8 | 2026-05-27 | 1,000,000 | 5 | 25 | Y | Y | - | - | optional |  |
| qwen/qwen3.7-max | 2026-05-21 | 1,000,000 | 1.48 | 4.42 | Y | Y | Y | Y | optional |  |
| x-ai/grok-build-0.1 | 2026-05-20 | 256,000 | 1 | 2 | Y | Y | Y | Y | mandatory |  |
| google/gemini-3.5-flash | 2026-05-19 | 1,048,576 | 1.5 | 9 | Y | Y | Y | Y | mandatory |  |
| google/gemini-3.1-flash-lite | 2026-05-07 | 1,048,576 | 0.25 | 1.5 | Y | Y | Y | Y | optional |  |
| openai/gpt-chat-latest | 2026-05-05 | 400,000 | 5 | 30 | Y | Y | - | Y | none |  |
| x-ai/grok-4.3 | 2026-04-30 | 1,000,000 | 1.25 | 2.5 | Y | Y | Y | Y | optional |  |
| mistralai/mistral-medium-3-5 | 2026-04-30 | 262,144 | 1.5 | 7.5 | Y | Y | Y | Y | optional |  |
| qwen/qwen3.5-plus-20260420 | 2026-04-26 | 1,000,000 | 0.3 | 1.8 | Y | Y | Y | Y | optional |  |
| qwen/qwen3.6-flash | 2026-04-26 | 1,000,000 | 0.188 | 1.12 | Y | Y | Y | Y | optional |  |
| qwen/qwen3.6-35b-a3b | 2026-04-26 | 262,144 | 0.1 | 0.9 | Y | Y | Y | Y | optional |  |
| qwen/qwen3.6-27b | 2026-04-26 | 262,144 | 0.45 | 2.7 | Y | Y | Y | Y | optional |  |
| openai/gpt-5.5-pro | 2026-04-24 | 1,050,000 | 30 | 180 | Y | Y | - | Y | mandatory |  |
| openai/gpt-5.5 | 2026-04-24 | 1,050,000 | 5 | 30 | Y | Y | - | Y | optional |  |
| deepseek/deepseek-v4-pro | 2026-04-23 | 1,048,576 | 1.6 | 3.2 | Y | Y | Y | Y | optional | 14 providers |
| deepseek/deepseek-v4-flash | 2026-04-23 | 1,048,576 | 0.091 | 0.182 | Y | Y | Y | Y | optional |  |
| moonshotai/kimi-k2.6 | 2026-04-20 | 262,144 | 0.65 | 3.41 | Y | Y | Y | Y | optional |  |
| anthropic/claude-opus-4.7 | 2026-04-16 | 1,000,000 | 5 | 25 | Y | Y | - | - | optional |  |
| z-ai/glm-5.1 | 2026-04-07 | 204,800 | 1.4 | 4.4 | Y | Y | Y | Y | optional |  |
| qwen/qwen3.6-plus | 2026-04-02 | 1,000,000 | 0.325 | 1.95 | Y | Y | Y | Y | optional |  |
| z-ai/glm-5v-turbo | 2026-04-01 | 202,752 | 1.2 | 4 | - | Y | Y | - | optional |  |
| anthropic/claude-haiku-4.5 | 2025-10-15 | 200,000 | 1 | 5 | Y | Y | Y | - | optional |  |

Providers column is filled only for the 16 models whose endpoints were queried; blank means not queried. No Meta Llama model created after 2026-04-01 appeared in the feed (older Llama slugs were not examined).
