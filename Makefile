BINARY := build/ambrosia
GOLANGCI_LINT ?= golangci-lint

.PHONY: build run test lint fmt tidy clean initialize-ambrosia

build:
	CGO_ENABLED=0 go build -o $(BINARY) .

run:
	go run ./main.go

test:
	go test ./...
	python3 -m unittest scripts/test_initialize_ambrosia.py

lint:
	$(GOLANGCI_LINT) run ./...

fmt:
	go fmt ./...

tidy:
	go mod tidy

initialize-ambrosia:
	python3 scripts/initialize-ambrosia.py

clean:
	rm -rf build
