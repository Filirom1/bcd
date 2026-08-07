{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "bcd-dev-environment";

  buildInputs = with pkgs; [
    # Python 3.13
    python313
    python313Packages.pip
    python313Packages.setuptools
    python313Packages.wheel
    python313Packages.virtualenv

    # Core dependencies from nixpkgs (pre-built)
    python313Packages.fastapi
    python313Packages.uvicorn
    python313Packages.sqlalchemy
    python313Packages.alembic
    python313Packages.pydantic
    python313Packages.pydantic-settings
    python313Packages.python-multipart
    python313Packages.jinja2

    # CLI dependencies
    python313Packages.click
    python313Packages.httpx
    python313Packages.rich

    # Integration dependencies
    python313Packages.requests

    # Utilities
    python313Packages.lxml
    python313Packages.zeroconf

    # pywebview system dependencies (GTK + WebKit2, uses OS-provided engine)
    gtk3
    webkitgtk_4_1
    gobject-introspection
    python313Packages.pygobject3

    # Testing
    python313Packages.pytest
    python313Packages.pytest-asyncio
    python313Packages.pytest-cov
    python313Packages.pytest-mock
    python313Packages.pytest-playwright
    playwright-driver.browsers

    # Development tools
    python313Packages.black
    python313Packages.mypy
    python313Packages.ipython

    # Additional tools
    sqlite
    # Runs Web UI tests and the Vite production build. FastAPI remains the
    # only development server; run `npm ci` once after entering the shell.
    nodejs_22
    typescript

    chromium
  ];

  shellHook = ''
    echo "BCD Development Environment"
    echo "Python version: $(python --version)"
    echo ""

    # Create virtualenv if it doesn't exist
    if [ ! -d "venv" ]; then
      echo "Creating Python virtual environment..."
      python -m venv venv
    fi

    # Activate virtualenv
    source venv/bin/activate

    # Set Playwright browser path for Nix
    export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
    export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

    # Set up Python path to include src directory
    export PYTHONPATH="${toString ./.}/src:$PYTHONPATH"

    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
      echo "Creating .env from .env.example..."
      cp .env.example .env
    fi
  '';
}
