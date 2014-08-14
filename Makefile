all:

.PHONY: test check clean build publish install

README.rst: README.md
	@pandoc -f markdown -t rst -o README.rst README.md

test:
	@nosetests tests/
check:
	@./setup.py check
clean:
	@rm -rf build/ dist/ *.egg-info/
build: README.rst
	@./setup.py build sdist bdist_wheel
publish: README.rst
	@./setup.py build sdist bdist_wheel register upload -r pypi
