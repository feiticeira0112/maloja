# Development

Clone the repository and enter it.

```console
	git clone https://github.com/krateng/maloja
	cd maloja
```

## Environment

To avoid cluttering your system, consider using a [virtual environment](https://docs.python.org/3/tutorial/venv.html).

Your system needs several packages installed. On Alpine, this can be done with

```console
	sh ./install/install_dependencies.sh
```

For other distros, try to find the equivalents of the packages listed or simply check your error output.

Then install all Python dependencies with

```console
	pip install -r requirements.txt
```


## Running the server

For development, you might not want to install maloja files all over your filesystem. Use the environment variable `MALOJA_DATA_DIRECTORY` to force all user files into one central directory - this way, you can also quickly change between multiple configurations.

You can quickly run the server with all your local changes with

```console
	python3 -m maloja run
```

You can also build the package with

```console
	pip install .
```
## Further help

Feel free to [ask](https://github.com/krateng/maloja/discussions) if you need some help!
