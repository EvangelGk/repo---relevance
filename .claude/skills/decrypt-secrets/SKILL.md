---
name: decrypt-secrets
description: Decrypt the tracked .env.enc into a local .env - works only if your age key is already a listed recipient in .sops.yaml. Backend/developer-only, not for anyone who just needs to use the app UI. Not for onboarding a new key - see /add-secrets-recipient for that, or /grant-secrets-access if you're the admin granting someone access.
---

# Decrypt the repo's secrets

Backend/developer-only. Target completion time: under 1 minute if you're
already a recipient, under 5 including a fresh install.

## Before anything else: are you in the right place?

This skill is for running this repo's code locally. If you only want to
**use** the app, stop here and go to **<APP_URL>** instead - sign in
with your work email, nothing to install.

**Precondition:** your age private key must already correspond to a
public key listed in `.sops.yaml`'s `key_groups.age`. If you're not sure
you're a recipient yet, run `/add-secrets-recipient` first, then wait for
the admin to run `/grant-secrets-access` before trying this.

## Steps to run

1. Confirm `sops` is on `PATH`; if missing:
   ```powershell
   winget install --id SecretsOPerationS.SOPS -e --silent
   ```
2. Confirm you have a private key `sops` can actually find - check both
   possible locations, don't assume the default:
   - `$env:SOPS_AGE_KEY_FILE`, if set, pointing at a file that exists; or
   - the default location, `%AppData%\sops\age\keys.txt` (sops's real
     Windows default - not the `~/.config/...` XDG path some docs/
     tutorials assume).
   If neither is found, stop and point at `/add-secrets-recipient` -
   don't generate a new key here, that's a different skill's job, and a
   freshly generated key wouldn't be a recognized recipient anyway.
3. Decrypt:
   ```powershell
   sops --input-type dotenv --output-type dotenv -d .env.enc > .env
   ```
   The explicit `--input-type`/`--output-type dotenv` flags are required
   - `.sops.yaml` has no way to pin the format itself (`input_type`/
   `output_type` are not real `creation_rules` keys). Relying on sops's
   filename-based guessing is exactly what silently broke this repo's
   first `.env.enc` - see "Secrets management (SOPS + age)" in
   `CLAUDE.md` for the full story.
4. **If it fails** with `Failed to get the data key` / `failed to load
   age identities`: you're not (yet) a listed recipient, or your key
   file/`SOPS_AGE_KEY_FILE` isn't pointing at the right place. Point at
   `/add-secrets-recipient` and stop - regenerating a key or retrying
   won't help until the admin runs `/grant-secrets-access` for your
   specific public key.
5. **If it succeeds**, confirm without ever printing values - list key
   *names* only:
   ```powershell
   Get-Content .env | ForEach-Object { ($_ -split '=')[0] }
   ```
   and remind that `.env` stays gitignored and must never be committed.

## Guardrails

- Never print decrypted secret values into chat, logs, or any file other
  than the local `.env` itself.
- Never commit `.env`.
- If decryption fails because the caller isn't a recipient yet, the fix
  is `/add-secrets-recipient` (self-service) plus the admin running
  `/grant-secrets-access` - this skill can't do either of those itself.
