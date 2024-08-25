# ragintel


<p align="center">
<a href="https://pypi.python.org/pypi/ragintel">
    <img src="https://img.shields.io/pypi/v/ragintel.svg"
        alt = "Release Status">
</a>

<a href="https://github.com/darkquasar/ragintel/actions">
    <img src="https://github.com/darkquasar/ragintel/actions/workflows/main.yml/badge.svg?branch=release" alt="CI Status">
</a>

<a href="https://darkquasar.github.io/ragintel/">
    <img src="https://img.shields.io/website/https/darkquasar.github.io/ragintel/index.html.svg?label=docs&down_message=unavailable&up_message=available" alt="Documentation Status">
</a>

</p>


Test


* Free software: BSD-3-Clause
* Documentation: <https://darkquasar.github.io/ragintel/>


## Features

* TODO

## Contribute and Test

### Generating Dev Environment

#### Clone this Repo

```powershell
git clone XXXXX
```

#### Install Mamba or Anaconda

TBD

#### Create Mamba Environment

```powershell
mamba env create --file ragintel-mamba-env.yaml
```

#### Install required packages using Poetry

```powershell
poetry install --with dev
```

#### Configure Git Pre-Commit Checks

```powershell
git init
git config init.defaultBranch main
git config user.name "YourName"
git config user.email "YourEmail@something.com"

pre-commit install

git remote add origin git@github.com:darkquasar/ragintel.git
git add .
pre-commit run --all-files
git add .
git commit -m "Initial contribution commit"
git branch -M main
git push -u origin main
```

### Destroying and Regenerating the Environment

To achieve this, we will destroy the Mamba virtual environment, then recreate it and add install all Poetry packages again

```powershell
# Delete poetry.lock
del poetry.lock

# Deactivate your ragintel env
mamba deactivate

# Delete environment
mamba env remove -n ragintel

# Create ragintel Mamba env again
mamba env create --file ragintel-mamba-env.yaml

# Re-Install all packages using Poetry
poetry install --with dev
```

### Installing for Embedchain JupyterNotebooks



## Credits

This package was created with the [Python Project Wizard](https://zillionare.github.io/python-project-wizard/) Cookiecutter template.
