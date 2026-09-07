# Serve wasmer/browser + artifacts for the challenge-first appliance.
FROM nginx:1.27-alpine
COPY services/browser-client/nginx.conf /etc/nginx/nginx.conf
COPY wasmer/browser/ /usr/share/nginx/html/
# challenge.html expects ../artifacts from browser/ → map artifacts at /artifacts and also sibling path
COPY wasmer/artifacts/ /usr/share/nginx/artifacts/
# Mirror layout expected by relative ../artifacts from /challenge.html
RUN mkdir -p /usr/share/nginx/wasmer && \
    ln -sfn /usr/share/nginx/artifacts /usr/share/nginx/wasmer/artifacts && \
    # Pages live at /; relative ../artifacts from /challenge.html resolves to /artifacts — good.
    true
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1/healthz || exit 1
