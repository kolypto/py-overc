all:

.PHONY: test check build publish install

test:
	@nosetests tests/
check:
	@./setup.py check
build:
	@./setup.py build sdist bdist
publish:
	@./setup.py build sdist bdist register upload -r pypi
install:
	@./setup.py install
