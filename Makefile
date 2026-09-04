test-all-fake:
	.venv/bin/python -m pytest workers/ --target fake

test-all-live:
	.venv/bin/python -m pytest workers/ --target live

test-fake:
	@f=$$(find workers -name "test_*.py" | fzf --prompt="test-fake> ") && [ -n "$$f" ] && .venv/bin/python -m pytest "$$f" --target fake -q

test-live:
	@f=$$(find workers -name "test_*.py" | fzf --prompt="test-live> ") && [ -n "$$f" ] && .venv/bin/python -m pytest "$$f" --target live -q
