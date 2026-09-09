.PHONY: secrets-encrypt secrets-decrypt

# Both targets pin --input-type/--output-type explicitly to dotenv. sops
# has no such key in .sops.yaml's creation_rules (input_type/output_type
# there are silently-ignored no-ops - CLI flags are the only way to set
# this) - without pinning it, sops guesses the format from each filename's
# extension, which disagrees between "sops -e .env" (sees ".env" -> dotenv)
# and "sops -d .env.enc" (sees ".enc" -> falls back to a JSON-ish guess),
# so decrypt always fails against what encrypt just wrote.

# Re-encrypt the local .env into the tracked .env.enc.
# Only ever run this with your own real, up-to-date .env - it overwrites
# .env.enc for everyone once committed.
secrets-encrypt:
	@command -v sops >/dev/null 2>&1 || { \
		echo "error: sops is not installed or not on PATH. Install it from https://github.com/getsops/sops and try again." >&2; \
		exit 1; \
	}
	sops --input-type dotenv --output-type dotenv -e .env > .env.enc

# Decrypt the tracked .env.enc into a local .env (gitignored, never committed).
# Requires your age private key to be set up - see "Secrets management
# (SOPS + age)" in CLAUDE.md.
secrets-decrypt:
	@command -v sops >/dev/null 2>&1 || { \
		echo "error: sops is not installed or not on PATH. Install it from https://github.com/getsops/sops and try again." >&2; \
		exit 1; \
	}
	sops --input-type dotenv --output-type dotenv -d .env.enc > .env
