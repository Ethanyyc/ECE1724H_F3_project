"""Check the LLM connection with one tiny call per model.

Reports whether ANTHROPIC_API_KEY is set, which models the Anthropic API lists,
and whether each model answers with adaptive thinking at its configured effort,
as the experiments call it.

Usage: python -m experiments.check_api [--models NAME ...]
"""

import argparse

from speccheck import config
from speccheck.llm import has_credentials, make_anthropic_client, role_effort


def error_message(error):
    """The API's own error message."""
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        for path in (("error", "message"), ("message",)):
            node = body
            for key in path:
                node = node.get(key) if isinstance(node, dict) else None
            if isinstance(node, str):
                return node
    return str(error)[:500]


def check_model(client, model, effort):
    request = {"model": model, "max_tokens": 2048, "messages": [{"role": "user", "content": "Reply with OK."}],
               "thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}
    try:
        response = client.messages.create(**request)
    except Exception as error:   # noqa: BLE001 - report any failure and go on
        print(f"{model} (adaptive thinking, {effort} effort): failed "
              f"({getattr(error, 'status_code', type(error).__name__)}): {error_message(error)}")
        return
    usage = response.usage
    details = getattr(usage, "output_tokens_details", None)
    print(f"{model} (adaptive thinking, {effort} effort): OK, answered by {response.model}; "
          f"{usage.input_tokens} input, {usage.output_tokens} output, "
          f"{getattr(details, 'thinking_tokens', None)} thinking tokens")


def main(argv=None):
    p = argparse.ArgumentParser(description="Check the LLM connection with one tiny call per model.")
    p.add_argument("--models", nargs="*", help="model ids to test (default: the writer and attacker models)")
    args = p.parse_args(argv)
    if args.models:
        targets = [(model, role_effort("attacker")) for model in args.models]
    else:
        targets = [(config.WRITER_MODEL, role_effort("writer")), (config.ATTACKER_MODEL, role_effort("attacker"))]

    print(f"ANTHROPIC_API_KEY set: {has_credentials()}")
    if not has_credentials():
        print("no credentials: set ANTHROPIC_API_KEY (see README)")
        return
    client = make_anthropic_client()
    try:
        ids = [m.id for m in client.models.list(limit=100)]
        print(f"models listed by the API: {', '.join(ids) if ids else '(none; try names with --models)'}")
    except Exception as error:   # noqa: BLE001 - report and go on to the model checks
        print(f"the API did not list models ({type(error).__name__}: {error_message(error)})")
    for model, effort in targets:
        check_model(client, model, effort)


if __name__ == "__main__":
    main()
