---
name: add-secrets-recipient
description: One-shot, self-service flow for a new backend/developer teammate to generate their own age keypair themselves (off Claude - the private key never enters this session), and get the public half added to .sops.yaml automatically. Backend-only, not for anyone who just needs to use the app UI. Does not decrypt or re-encrypt anything - see /decrypt-secrets and /grant-secrets-access for those.
---

# Add yourself as a secrets recipient

Backend/developer-only. Target completion time: under 5 minutes.

## Before anything else: are you in the right place?

This skill is for someone who needs to run this repo's code locally
(CLI, pytest, or `streamlit run` on their own machine) - not for someone
who just wants to use the app. If you only need to **use** the tool,
stop here and go to the app instead: **<APP_URL>** (ask the admin if you
don't have this link yet - sign in there with your work email, nothing
to install).

Ask the person plainly: "Do you need to run this repo's Python code
yourself, or do you just want to use the app through a browser?" If it's
the second one, redirect them to the URL above and stop - do not proceed
with anything below.

**Also ask:** "Do you already have an age keypair you use for this repo
(or want to reuse one from elsewhere)?" If yes, skip straight to Step 3
with their existing `age1...` public key - generating a second,
unnecessary keypair just leaves a stale, unused entry in `.sops.yaml`.

## Steps to run

### Step 1 - install the tools (automated, safe - no secret material involved)

Check `sops` and `age` are on `PATH`. If either is missing, install via
winget:
```powershell
winget install --id SecretsOPerationS.SOPS -e --silent
winget install --id FiloSottile.age -e --silent
```
Re-check both afterward (`sops --version`, `age-keygen --version`) - a
fresh terminal may be needed for `PATH` to pick up a just-installed tool,
and winget itself may need to be run elevated on a locked-down machine.
If winget isn't available at all, fall back to
https://github.com/getsops/sops/releases and
https://github.com/FiloSottile/age/releases.

### Step 2 - generate your keypair yourself, in your own terminal (manual - Claude never runs this)

This is the one step Claude never executes and never sees the output of.
Copy this exact command and run it **yourself**, in your own terminal
window, separate from this chat:

```powershell
age-keygen
```

It prints three lines: a `# created:` timestamp, a `# public key:
age1...` line, and the actual private key line `AGE-SECRET-KEY-1...`.

**Do this now, before continuing:**
1. Copy the `AGE-SECRET-KEY-1...` line and save it somewhere durable and
   secure that you control - a password manager or an encrypted note.
   Saving it is entirely your own responsibility from here.
2. If you lose it, there is no recovery path - you'd generate a brand
   new keypair and get re-added as a recipient from scratch.
3. `sops` will look for this key later at its default location,
   `%AppData%\sops\age\keys.txt` (zero extra config needed), or anywhere
   else if you set `$env:SOPS_AGE_KEY_FILE` to point at it. If a
   `keys.txt` already exists there from another project, you can append
   this new block instead of replacing it - age supports multiple
   identities in one file.
4. Once it's saved, come back and paste **only the `age1...` public key
   line** into this chat - never the `AGE-SECRET-KEY-1...` line.

Because Claude never runs this command, the private key never enters
this conversation, its history, or any logging surface tied to it.
That's the whole reason this step works this way instead of Claude
generating and displaying it for you.

### Step 3 - register your public key (automated, safe - public keys aren't secret)

Once you have the `age1...` line:
1. Read the current `.sops.yaml` fresh.
2. Append the new public key as a new line under the existing
   `key_groups: - age:` list, preserving every key already there - don't
   remove or reorder existing entries.
3. If this exact public key is already present, say so and stop instead
   of adding a duplicate.

### Step 4 - report back and hand off to the admin

- Confirm the public key was added to `.sops.yaml`.
- Explain clearly: `.env.enc` is **not re-encrypted for you yet** - you
  are registered but cannot decrypt anything until the admin runs
  `/grant-secrets-access` (a separate, admin-only skill, deliberately -
  see that skill's file for why).
- Tell them to message the admin now and ask them to run it.
- Once the admin confirms it's done, they run `/decrypt-secrets` to get
  their own working `.env`.

## Guardrails

- Never run `age-keygen` yourself - Step 2 is the person's own terminal,
  every time, no exceptions.
- Never ask the person to paste the private key back into this chat -
  only the public key line is ever needed here.
- This skill only ever edits `.sops.yaml` - it never touches `.env` or
  `.env.enc`, and never runs `sops -e`/`sops -d`.
- Don't commit or push anything - leave the `.sops.yaml` change
  staged/unstaged for the admin to review and commit.
