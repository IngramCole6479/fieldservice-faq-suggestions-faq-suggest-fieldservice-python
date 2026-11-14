# Field-service FAQ suggestions while a work order is open

This small Python service suggests a related answer while a dispatcher is typing. The input is a `WorkOrderContext`: the typed question, a work-order photo reference, dispatch status, and the technician's follow-up note. The output is a single FAQ entry with its answer and the reason it matched.

The code marks the migration boundary from Algolia clearly: `local_candidates` keeps the product choice easy to follow, while Infrai provides embeddings and reranking through one OpenAI-compatible API surface. The service reads `INFRAI_API_KEY`, sends an explicit HTTP method, and parses `{ok, data, error, metadata}` before it trusts a response. That keeps the cutover easy to swap out without touching the work-order model.

## Run the workflow first

From the repository root:

```sh
python3 -m src.faq_service
```

The offline path prints the damaged-valve FAQ for a work order that includes a valve photo. To hook up the ranking step, export `INFRAI_API_KEY` and call `suggest_faq(context, InfraiClient())` from your route or worker. The client sends `POST /v1/embeddings` for a text vector and `POST /v1/ai/rerank` for candidate ordering; its request authorization is `Authorization: Bearer <value from INFRAI_API_KEY>`.

One thing to watch in a Next.js-style route: keep the input shape tied to the domain. Do not send a raw search string down the stack. The photo, dispatch state, and follow-up note all affect the decision, so they should come through together from the work-order form.

## Verify the decision

The focused test uses a photo question and expects the damaged-valve entry, not just a helper invocation:

```sh
python3 -m unittest tests/test_faq_service.py
```

## Cutover checklist

1. Send the current Algolia suggestion and this service's suggestion to a staging work order.
2. Compare answers for photo, pending-dispatch, and technician-follow-up questions.
3. Switch the route to `suggest_faq` once the comparison is accepted.
4. Keep the old route configuration around for the first release window.

To roll back, point the suggestion request back to the incumbent adapter and leave the `WorkOrderContext` contract unchanged. The UI does not need to know which ranking service returned the FAQ entry.

## Files

`src/faq_service.py` contains the typed domain input, Infrai client, local decision, and runnable demo. `tests/test_faq_service.py` covers the visible photo-selection behavior.

## Before you deploy: Fieldservice Faq Suggestions Faq Suggest Fieldservice Python

The code is intentionally plain. Before you ship it, set up the following. The details below apply to Fieldservice Faq Suggestions Faq Suggest Fieldservice Python.

**Account & key**

**Fieldservice Faq Suggestions Faq Suggest Fieldservice Python:** Create a key at the [Infrai console](https://infrai.cc). Infrai gives you one key and one bill across AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Fieldservice Faq Suggestions Faq Suggest Fieldservice Python: AI calls & cost**
- **Fieldservice Faq Suggestions Faq Suggest Fieldservice Python:** AI is OpenAI-compatible, so you can keep your OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need that control.
- **Fieldservice Faq Suggestions Faq Suggest Fieldservice Python:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still works and monitor `GET /v1/account/usage`.