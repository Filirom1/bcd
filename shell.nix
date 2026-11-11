{ pkgs ? import <nixpkgs> {} }:

let
  # Keep the interpreter and its libraries/plugins in one Python environment.
  # Listing python3Packages individually in mkShell only adds their executables
  # to PATH; `python -m pytest` then cannot import them.
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    pip
    setuptools
    wheel
    virtualenv

    # Core dependencies
    fastapi
    uvicorn
    sqlalchemy
    alembic
    pydantic
    pydantic-settings
    python-multipart
    jinja2

    # CLI dependencies
    click
    httpx
    rich

    # Integration dependencies
    requests

    # Utilities and GTK integration
    lxml
    zeroconf
    pygobject3

    # Testing
    pytest
    pytest-asyncio
    pytest-cov
    pytest-playwright

    # Development tools
    black
    mypy
    ipython
    pyinstaller
  ]);
in
pkgs.mkShell {
  name = "bcd-dev-environment";

  buildInputs = with pkgs; [
    pythonEnv

    # pywebview system dependencies (GTK + WebKit2, uses OS-provided engine)
    gtk3
    webkitgtk_4_1
    gobject-introspection

    # Godot 4.6 headless client tests
    godot
    playwright-driver.browsers

    # Additional tools
    sqlite
    # Runs Web UI tests and the Vite production build. FastAPI remains the
    # only development server; run `npm ci` once after entering the shell.
    nodejs_22
    typescript

    chromium
  ];

  shellHook = ''
    # Prefer the Python environment containing both the interpreter and its
    # packages over any parent shell's venv or standalone Python executables.
    unset VIRTUAL_ENV
    export PATH="${pythonEnv}/bin:$PATH"

    echo "BCD Development Environment"
    echo "Python version: $(python --version)"
    echo ""

    # Set Playwright browser path for Nix
    export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
    export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

    # Set up Python path to include src directory
    export PYTHONPATH="${toString ./.}/src"

    # Create .env only when the path is genuinely absent. Some CI/dev
    # harnesses expose secrets as a special file at .env; never overwrite it.
    if [ ! -e .env ]; then
      echo "Creating .env from .env.example..."
      cp .env.example .env
    fi
  '';
}
