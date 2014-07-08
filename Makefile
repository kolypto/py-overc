all:

.PHONY: test check build publish install

README.rst: README.md
	@pandoc -f markdown -t rst -o README.rst README.md

test:
	@nosetests tests/
check:
	@./setup.py check
build: README.rst
	@./setup.py build sdist bdist
publish: README.rst
	@./setup.py build sdist bdist register upload -r pypi
