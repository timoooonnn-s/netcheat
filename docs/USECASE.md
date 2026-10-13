# Use case: netcheat

## Problem

Day-to-day network operations on an Extreme Fabric Engine (VOSS) fabric need a large set of commands, but only a
handful of them are used daily. The rest (CFM traces, FIB and LSDB views, DvR host entries, MACsec/MKA, NAC session
handling, scheduled-reboot safety nets...) are needed rarely. When they are needed, it is usually during an incident.
They are easy to forget, and the official documentation is large and organized by CLI mode, not by task.

Some Juniper SRX firewalls also act as routers. They are touched rarely, so the basic Junos operational commands are
forgotten even faster.

## Goal

A personal and team **inventory of commands**, so useful commands are not forgotten:

- Find the right command in seconds from the terminal, offline, also while connected to a switch.
- Organize by task and topic (SPBM, L2/L3 VSN, DvR, SMLT/vIST, NAC, MACsec...), not by CLI mode.
- Mark commands that are rarely used but valuable ("gems"), so you can browse them on purpose (`ncs -r`, `ncs tip`).
- Give guided **troubleshooting flows** for the common problems, and short **concept** notes for the building blocks.
- **Browse** when you only have a broad idea (`ncs browse`), and **describe a problem in your own words** to get the
  matching flow and commands (`ncs fix`), offline, using symptom phrasings and an editable synonym list.
- **Tab completion** in zsh and bash for options, topics, flow ids and search words.
- Be precise: every Fabric Engine command is checked against the official documentation, links to it, and is tagged
  with the release that introduced it, when that release is newer than 9.1.

## Users

- Primary: a junior network engineer (about 14 months of experience) with an Extreme Fabric background and no Cisco
  background. Cisco equivalents are only given where they help as orientation.
- Secondary: the rest of the network team. The README therefore focuses on usage, and installing is a `git clone`
  plus `pip install -e .`.

## Environment and versions

- Extreme Fabric Engine up to **9.4.1** in production, **9.4.2** being rolled out in engineering (as of October 2026).
- Commands that appeared in a later release carry `since` (for example `"9.3"`). Commands that changed mode or name
  are noted (for example `show fulltech` is Privileged EXEC since 9.2, and `show ssh` was split in 9.3).
- NAC: ExtremeControl (XIQ-SE NAC) as RADIUS server, with EAP/NEAP, CoA, Auto-sense ports and dynamic I-SID assignment.
- Juniper: SRX used as a router; only about 20 basic operational commands, routing first.

## Scope

In scope:

- Fabric Engine operational and configuration commands: system/CLI/files/upgrade, ports/VLANs/loop protection,
  SPBM/IS-IS and fabric OAM (CFM, l2 ping/traceroute), L2 VSN/I-SID services, L3 VSN/VRF/routing, DvR and Anycast
  Gateway, MLT/SMLT/vIST/LACP, NAC (EAP/NEAP/RADIUS), Auto-sense/Fabric Attach/Zero Touch, MACsec.
- Juniper SRX routing basics and the safe-change workflow (commit confirmed).
- Troubleshooting flows and concept explanations.

Out of scope (on purpose):

- Complete configuration templates or runbooks (single commands with short examples only).
- Other Extreme operating systems (EXOS/Switch Engine, ERS/BOSS) and management platforms.
- A copy of the vendor documentation. Entries are short summaries and link to the official pages.

## Design decisions

| Decision | Reason |
|---|---|
| YAML data files as the single source | Easy to read and edit by hand, with clean diffs in Git. CLI and Markdown are generated from the same data, so nothing is maintained twice. |
| Python CLI `ncs` (rich, PyYAML) | Fast fuzzy search in the terminal, works offline, readable colored output. `ncs` instead of `nc`, so netcat is not shadowed. |
| Generated Markdown (`ncs build-md`) | Browsable on GitLab without installing anything, and printable. |
| Strict validation of the data | Hand edits by several people stay consistent. Errors name the file and entry, and tests check references and links. |
| Unicode icons instead of emoji | Consistent rendering in every terminal font, as requested. |
| `ncs add` appends text instead of rewriting YAML | Comments and layout of the hand-maintained files are preserved. |
| `ncs fix` is keyword and synonym matching, not AI | Works on jump hosts without internet, sends no problem descriptions anywhere, and is deterministic and testable. Wording is improved by editing `synonyms.yaml` and flow `symptoms`. |
| Browser built with Textual | From the authors of rich (already used), pure Python, works over SSH; it reuses the same render blocks as the CLI. |
| Completion via `ncs __complete` | One small shell function per shell; candidates come from the argparse definition and the data, so they never drift. |

## Sources

Primary (official Extreme Networks documentation):

- Fabric Engine 9.4 Command References (Rev AC) and Fabric Engine 9.4 User Guide (Rev AC)
- Fabric Engine 9.1, 9.2 and 9.3 Command References, compared to find the release that introduced each command
- Fabric Engine release notes 9.2, 9.3, 9.4, 9.4.1 and 9.4.2

Secondary:

- Extreme community forum (community.extremenetworks.com), used only for practical hints; such hints say so in the
  entry's notes.
- Juniper TechLibrary for the Junos commands.

Limits: the content has not been tested on our own hardware. Output fields and defaults can differ by platform and
release, so check unfamiliar configuration commands in the lab first.
