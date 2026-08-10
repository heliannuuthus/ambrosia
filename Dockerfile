FROM alpine:3.22

RUN apk add --no-cache ca-certificates
WORKDIR /app
COPY build/ambrosia /app/ambrosia

USER 65532:65532
ENTRYPOINT ["/app/ambrosia"]
