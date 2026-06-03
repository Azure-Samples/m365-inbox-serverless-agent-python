FROM mcr.microsoft.com/vscode/devcontainers/python:dev-3.12-bookworm

COPY first-run-notice.txt /usr/local/etc/vscode-dev-containers/first-run-notice.txt

RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - \
    && sudo apt-get install -y nodejs \
    && sudo npm install -g azure-functions-core-tools@4 \
    && sudo npm install -g @modelcontextprotocol/inspector \
    && sudo npm install -g azurite \
    && curl -fsSL https://aka.ms/install-azd.sh | bash \
    && curl -fsSL https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh
