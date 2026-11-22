IMAGE ?= blast-radius-entry
LAB_IMAGE ?= blast-radius-lab
SAMPLE := $(CURDIR)/sample
OUTPUT := $(CURDIR)/output.jsonl
STDERR_LOG := $(CURDIR)/output.stderr.log

SQLGLOT_URL := https://github.com/tobymao/sqlglot.git
SQLGLOT_SHA := eb11aec4be8cb2122afe713a4816662c3f0fb2fa
VENDOR := $(CURDIR)/vendor/sqlglot

# Keep in sync with CMD in the Dockerfile.
SELECTOR_CMD := python -m selector

# The flags the scorer runs your image with. The scorer is linux/amd64, so on
# an Apple Silicon Mac --platform makes your local run match it.
RUN_FLAGS := --rm --platform linux/amd64 --network none --cpus 2 \
	--memory 4096m --memory-swap 4096m --pids-limit 256 --read-only \
	--tmpfs /tmp:rw,size=64m,mode=1777 --cap-drop ALL \
	--security-opt no-new-privileges --user 65534:65534 --env HOME=/tmp \
	--volume $(SAMPLE)/commits:/data/commits:ro \
	--volume $(SAMPLE)/tests.json:/data/tests.json:ro

# The lab runs as you, with the repo mounted at /work (see tools/lab.Dockerfile).
LAB_FLAGS := --rm --platform linux/amd64 --user $(shell id -u):$(shell id -g) \
	--volume $(CURDIR):/work

.PHONY: build sample sample-cpu check local sqlglot lab lab-shell lab-run

## --- Starter-kit targets (scorer-equivalent) --------------------------------

build:
	docker build --platform linux/amd64 --tag $(IMAGE) .

# Runs your image once on the sample commits under the scorer's limits and
# scores what it printed.
sample: build
	docker run $(RUN_FLAGS) $(IMAGE) > $(OUTPUT)
	python3 score.py $(SAMPLE) $(SAMPLE)/answers.json $(OUTPUT)

# The output's rules only: every line well formed and every commit answered.
# A wrong selection still passes here; make sample counts the misses.
check: build
	docker run $(RUN_FLAGS) $(IMAGE) > $(OUTPUT)
	python3 score.py $(SAMPLE) $(SAMPLE)/answers.json $(OUTPUT) > /dev/null && echo "format ok"

## --- Our targets ------------------------------------------------------------

# Like sample, plus the selector's CPU seconds measured inside the container,
# so the Total line approximates one board run.
sample-cpu: build
	@docker run $(RUN_FLAGS) --volume $(CURDIR)/tools/cputime.py:/cputime.py:ro \
		--entrypoint python $(IMAGE) /cputime.py $(SELECTOR_CMD) \
		> $(OUTPUT) 2> $(STDERR_LOG); status=$$?; cat $(STDERR_LOG) >&2; exit $$status
	python3 score.py $(SAMPLE) $(SAMPLE)/answers.json $(OUTPUT) \
		--cpu-seconds $$(sed -n 's/^cputime: //p' $(STDERR_LOG) | tail -n 1)

# Fast loop on the host, no Docker. Host Python may differ from the image and
# CPU is not measured, so confirm with make sample before submitting.
local:
	BLAST_DATA=$(SAMPLE) python3 -m selector > $(OUTPUT)
	python3 score.py $(SAMPLE) $(SAMPLE)/answers.json $(OUTPUT)

# Shallow-clone sqlglot at the pinned commit into vendor/sqlglot (gitignored).
sqlglot:
	@if [ "$$(git -C $(VENDOR) rev-parse HEAD 2>/dev/null)" != "$(SQLGLOT_SHA)" ]; then \
		mkdir -p $(VENDOR) && git -C $(VENDOR) init -q && \
		(git -C $(VENDOR) remote get-url origin >/dev/null 2>&1 || \
			git -C $(VENDOR) remote add origin $(SQLGLOT_URL)) && \
		git -C $(VENDOR) fetch -q --depth 1 origin $(SQLGLOT_SHA) && \
		git -C $(VENDOR) checkout -q --detach FETCH_HEAD; \
	fi
	@echo "vendor/sqlglot at $$(git -C $(VENDOR) rev-parse HEAD)"

# The labeling environment: same base image + requirements.lock.
lab:
	docker build --platform linux/amd64 --file tools/lab.Dockerfile --tag $(LAB_IMAGE) .

lab-shell: lab sqlglot
	docker run -it $(LAB_FLAGS) $(LAB_IMAGE) bash

# make lab-run CMD="python -m pytest -q -p no:cacheprovider tests/test_serde.py"
# Runs in vendor/sqlglot; the repo is at /work.
lab-run: lab sqlglot
	docker run $(LAB_FLAGS) $(LAB_IMAGE) $(CMD)
