all:

.PHONY: check build publish

check:
	@./setup.py check
build:
	@./setup.py build sdist bdist_egg
publish:
	@./setup.py build sdist bdist_egg register upload -r pypi
