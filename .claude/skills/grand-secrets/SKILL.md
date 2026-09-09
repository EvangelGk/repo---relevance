---
name: grant-secrets-access
description: Admin-only. Re-encrypts .env.enc for every public key currently listed in .sops.yaml, actually granting decrypt access to anyone newly added via /add-secrets-recipient. This is the real access-control checkpoint in this repo's secrets setup - deliberately never automatic, never run by anyone but the admin.
---

# Grant secrets access (re-encrypt .env.enc)

Admin-only. Target completion time: under 5 minutes.

## Stop and confirm before anything else

This skill performs the actual access grant. The moment it finishes,
every public key currently listed in `.sops.yaml` can decrypt this
repo's real, live API keys. It is not self-service, and it is not meant
to be run by anyone who isn't the repo admin.

Ask plainly: "Are you the admin of this repo?" If there's any doubt at
all, stop now and don't proceed - point them to the admin instead. This
question is a friction check, not the actual security boundary. The real
boundary is structural, not procedural: this skill can only succeed if
the person running it already has a working age private key that's
already a valid recipient, because re-encrypting a file requires
decrypting it first. Someone who isn't already a recipient cannot make
this skill succeed no matter what they type here. Still ask, and still
stop if the answer isn't a clear yes - the question catches an
accidental run, the cryptography catches everything else.

## Steps to run

### Step 1 - show what's about to change (review before acting)

Show the admin what's changed in `.sops.yaml` since the last encryption,
so they can see exactly who's about to gain access:
```powershell
git diff .sops.yaml
```
Summarize in plain language: "These public keys will be able to decrypt
`.env.enc` once you continue: [list]. If any of these weren't added by
someone you recognize going through `/add-secrets-recipient`, stop now."

Ask the admin to explicitly confirm before continuing - a plain "yes,
proceed" in chat is enough, but don't continue without it.

### Step 2 - make sure a current, decrypted `.env` exists

If the admin doesn't already have an up-to-date plaintext `.env` locally,
decrypt the current `.env.enc` with their own key first:
```powershell
sops --input-type dotenv --output-type dotenv -d .env.enc > .env
```
If this fails, stop - it means the admin's own key isn't currently a
valid recipient, which shouldn't happen. Surface the error as-is, don't
troubleshoot around it silently.

### Step 3 - re-encrypt for the full current recipient list

Check for `make` first; use it if present, otherwise the raw command:
```powershell
make secrets-encrypt
```
or, if `make` isn't on `PATH`:
```powershell
sops --input-type dotenv --output-type dotenv -e .env > .env.enc
```
This re-encrypts `.env.enc` for every key currently listed in
`.sops.yaml`, including any newly added since the last encryption.

### Step 4 - confirm without exposing anything

- Confirm the command completed with no error.
- **Never print any decrypted value from `.env`** at any point in this
  skill - not even key names, this skill handles the real ciphertext.
- Report which public keys are now valid recipients (by key, never by
  value) and remind the admin that `.env.enc` (and `.sops.yaml` if it
  changed) are staged for them to review and commit themselves.
- Tell the newly-added teammate they can now run `/decrypt-secrets`.

## Removing someone (offboarding) - same skill, opposite direction

If instead a recipient is being **removed** (someone left, or a key was
compromised): delete their line from `.sops.yaml` first, then run
`sops updatekeys .env.enc` (not `secrets-encrypt`) so the ciphertext is
rewritten without their key entirely - simply deleting the line from
`.sops.yaml` does not retroactively revoke access to an already-encrypted
file. Confirm with the admin the same way as Step 1 before doing this.

```powershell
sops updatekeys .env.enc
```

## Guardrails

- Never run this without an explicit "yes" from a confirmed admin.
- Never print decrypted `.env` contents into chat, logs, or anywhere but
  the local `.env` file.
- Never commit or push - leave `.env.enc` (and `.sops.yaml` if changed)
  staged for the admin to review and commit.
- If in doubt about whether someone is really the admin, stop and do
  nothing rather than guess.
