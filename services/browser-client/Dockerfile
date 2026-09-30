# Serve wasmer/browser + artifacts for the challenge-first appliance.
# Stage 1 copies @wasmer/sdk (browser entrypoint + wasm) so Zone A can
# dynamic-import /browser without baking node_modules into git.
FROM node:22-alpine AS sdk
WORKDIR /sdk
COPY wasmer/browser/package.json wasmer/browser/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts

FROM nginx:1.27-alpine
COPY services/browser-client/nginx.conf /etc/nginx/nginx.conf
COPY wasmer/browser/ /usr/share/nginx/html/
COPY --from=sdk /sdk/node_modules/@wasmer/sdk /usr/share/nginx/html/vendor/@wasmer/sdk
# challenge.html expects ../artifacts from browser/ → map artifacts at /artifacts and also sibling path
COPY wasmer/artifacts/ /usr/share/nginx/artifacts/
COPY wasmer/fixtures/ /usr/share/nginx/fixtures/
# Mirror layout expected by relative ../artifacts from /challenge.html
RUN mkdir -p /usr/share/nginx/wasmer && \
    ln -sfn /usr/share/nginx/artifacts /usr/share/nginx/wasmer/artifacts && \
    ln -sfn /usr/share/nginx/fixtures /usr/share/nginx/wasmer/fixtures && \
    # Pages live at /; relative ../artifacts from /challenge.html resolves to /artifacts — good.
    true
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1/healthz || exit 1
