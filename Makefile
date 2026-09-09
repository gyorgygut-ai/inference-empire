test-all-fake:
	uv run --locked pytest workers/ --target fake

test-all-live:
	uv run --locked pytest workers/ --target live

test-fake:
	@f=$$(find workers -name "test_*.py" | fzf --prompt="test-fake> ") && [ -n "$$f" ] && uv run --locked pytest "$$f" --target fake -q

test-live:
	@f=$$(find workers -name "test_*.py" | fzf --prompt="test-live> ") && [ -n "$$f" ] && uv run --locked pytest "$$f" --target live -q

generate:
	@f=$$(find cli -name '*.md' | fzf --prompt='generate> ') && [ -n "$$f" ] && uv run --locked python cli/generate.py "$$f"
