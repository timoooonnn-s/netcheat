# Backlog

Features for `ncs`, ranked. Ground rules for everything here:

- **Offline only.** No web access, no AI, no online lookups. The tool runs on a Linux box reached over SSH.
- **Terminal only.** Plain CLI output or the full-screen terminal UI (`ncs browse`). Nothing web-browser based.
- **Never touches a switch.** The tool prints commands; you review and paste them.
- **Verified data.** New Fabric Engine content is checked against the official docs before it goes in.

Sizes are rough: S = an evening, M = a few sessions, L = a larger piece with its own design work.

| # | Feature | Priority | Size | Depends on |
|---|---|---|---|---|
| 1 | [Check the undo rules against real `show running-config`](#1-check-the-undo-rules-against-real-show-running-config) | **High** | S | show-run samples |
| 5 | [Sample outputs for show commands](#5-sample-outputs-for-show-commands) | Mid to high | M (mostly data) | real outputs |
| 8 | [Jump from a flow step to its command entry](#8-jump-from-a-flow-step-to-its-command-entry) | Medium | S | |
| 10 | [`ncs audit`: findings in a pasted config](#10-ncs-audit-findings-in-a-pasted-config) | Nice to have, if realistic | M | |
| 12 | [`ncs quiz`](#12-ncs-quiz) | Low | S | |
| 13 | [`ncs check`: validate the YAML without pytest](#13-ncs-check) | Mid (new) | S | |
| ? | [Team overlay](#team-overlay-waiting-for-a-decision) | Waiting for a decision | M | |

Not ranked yet: [tick off workflow steps](#not-ranked-yet), [personal notes per command](#not-ranked-yet).
[Done in 2.0.0](#done-in-200). [Dropped](#dropped): `ncs verify`, `ncs add`, the release filter, Cisco equivalents,
GitLab CI.

---

## 1. Check the undo rules against real `show running-config`

`ncs undo` and `ncs what` are built (2.0.0). Their rules come from the 9.4 command syntax and Extreme KB articles,
not from our own switches. Needed: sanitized excerpts of `show running-config module radius`, `module tacacs`,
`module ntp`, `module sys` (SNMP, syslog, users, DNS). Then: add them as test fixtures, fix any rule whose line ends
up under "No rule", and confirm the forms marked as manual (masked communities, engine-id users).
Later, topic by topic, rules for data-plane configuration could follow, each with real samples first.

## 5. Sample outputs for show commands

**What:** an optional `output:` field on show commands: a short, sanitized sample output, with what to look at.
Shown in the detail view (`-d`, browser, Markdown).

**Effort:** the code is small; the work is the data. Start with the commands used in the troubleshooting flows
(about 30).

**Open question:** real outputs from your switches (sanitized: hostnames, IPs, MACs, serials). Outputs from the
official docs could fill gaps, but they are often from older releases.

## 8. Jump from a flow step to its command entry

In the browser, step through the commands of a flow and open the matching command entry (notes, caution, docs link),
then go back. The matcher of `ncs what` (`config.explain`) already finds the entry for a step command, so this is
mostly browser work.

## 10. `ncs audit`: findings in a pasted config

**What:** paste or pipe a running config, get findings from fixed rules, each with the command that fixes it.
Examples: default `public`/`private` communities, telnet daemon on, no NTP server, syslog off, SNMPv1/v2c only, EAP
on but no `used-by eapol` server, SSH off.

**Realistic if:** rules stay simple ("line present" / "line missing"). Built on the line reader and matcher of
`ncs undo`. Start with 10 to 15 rules and only add rules with a clear fix. No scoring, no compliance claims.

## 13. `ncs check`

Validate the data files and print the same messages the loader does, without needing pytest installed. It took
`ncs add`'s place: content is edited in the YAML files now, so the thing that is actually missing is a quick
"did I break it?" for a colleague who only adds a command. Should also run the data rules the tests check
(`ref` present, no duplicate command per platform and mode, undo rules win for their own line, lock-out
removals carry a note).

## 12. `ncs quiz`

Flashcards from the gems: you see the description and recall the command, or the other way round. Reveal with a
key, mark known or not known. The score is kept locally next to the favourites, and unknown cards come back more often.

---

## Team overlay (waiting for a decision)

A second, optional data folder with company-specific content, kept separate from the generic cheatsheet. See the
discussion on 2026-10-15. Decide after: is the team going to write content for it, or is it just you?

## Not ranked yet (continued)

- **Tick off workflow steps:** mark steps done during a change in the browser; progress is kept locally.
- **Personal notes per command:** your own line under any entry, stored locally, shown in the detail view.

## Dropped in 3.0.0

`ncs add`, the release filter (`-R`, `NCS_RELEASE`, `-s/--since`) and the `cisco:` and `removed:` fields are gone;
see [Dropped](#dropped) for why. `rare:` went from 207 commands to 43. Removals that can lock you out of a switch
now carry a note, so `ncs undo` keeps them out of the paste-ready block.

## Done in 2.0.0

- `ncs undo`: removal commands from pasted configuration, in a safe order, risky ones flagged (was #1).
- `ncs what`: explain a command or configuration line, abbreviations included (was #2).
- `ncs` opens the browser; flow ids and concept names open from the search; `ncs list` replaces `ncs topics`,
  `ncs flow` and `ncs concept` (was #3).
- Favourites and recent entries (was #4).
- `ncs export`: a flow as a text or Markdown change plan with generated rollback (was #6).
- Copy a whole flow step in the browser with `1` to `9` (was #7).
- Placeholders: `{name}` values in every flow, `--set` and `v` in the browser (was #9).
- Placeholders, favourites, exports: see above.

## Not ranked yet

- **`verified:` per command:** who checked this command on which switch, and when. The content is still only
  checked against the documentation, which is the tool's weakest point; a date and a box turn "probably right"
  into "checked". Would supersede #1.
- **`-k` / `-p` in the browser:** the CLI has four filters, the browser has topic and gems only.
- **`?` keys screen in the browser:** the footer truncates, and the README is far away over SSH.

## Dropped

- `ncs verify` (needs web access to the docs).
- `ncs add` (2026-10-16): it could not ask for `ref`, `caution` or `undo` rules, so every entry it wrote failed
  the data tests; it also wrote into the installed package on a non-editable install. Edit the YAML instead.
- The release filter `-R` / `NCS_RELEASE`, `-s/--since` and the `removed:` field (2026-10-16): a lot of surface
  for 19 of 420 commands, and `removed:` was never set on a single one. `since:` stays as a badge.
- Cisco equivalents (`cisco:`, 2026-10-16): 140 unverifiable mappings written without a Cisco background. A wrong
  equivalent is worse than none. Add them back only with a citation each.
- GitLab CI (not needed).
- Anything online, AI-based or web-browser based.
