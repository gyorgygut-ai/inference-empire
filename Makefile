test-all-fake:
	.venv/bin/python -m pytest workers/ --target fake

test-all-dev:
	.venv/bin/python -m pytest workers/ --target live

test-fake:
	@f=$$(find workers -name "test_*.py" | fzf --prompt="test-fake> ") && [ -n "$$f" ] && .venv/bin/python -m pytest "$$f" --target fake -q

test-dev:
	@f=$$(find workers -name "test_*.py" | fzf --prompt="test-dev> ") && [ -n "$$f" ] && .venv/bin/python -m pytest "$$f" --target live -q
