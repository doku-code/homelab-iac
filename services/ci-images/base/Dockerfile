FROM node:22-bookworm

ARG GITLEAKS_VERSION=8.30.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash git git-lfs curl ca-certificates jq openssh-client gnupg tar && \
    rm -rf /var/lib/apt/lists/*

# Infisical CLI installation follows the existing CI toolchain convention.
RUN curl -fsSL https://artifacts-cli.infisical.com/setup.deb.sh -o /tmp/infisical-setup.sh && \
    bash /tmp/infisical-setup.sh && \
    apt-get update && apt-get install -y --no-install-recommends infisical && \
    rm -rf /var/lib/apt/lists/* /tmp/infisical-setup.sh

RUN test "$(dpkg --print-architecture)" = amd64 && \
    curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
      -o /tmp/gitleaks.tar.gz && \
    tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks && \
    chmod 0755 /usr/local/bin/gitleaks && rm /tmp/gitleaks.tar.gz

RUN bash --version && git --version && git-lfs --version && curl --version && \
    jq --version && ssh -V && node --version && infisical --version && gitleaks version
