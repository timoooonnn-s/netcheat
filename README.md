# netcheat

`ncs` is a command cheatsheet for the terminal. It covers **Extreme Fabric Engine (VOSS)** in depth and the
**Juniper SRX** troubleshooting basics: 420 commands with descriptions, examples, notes, Cisco equivalents and links to
the official documentation, 14 troubleshooting flows, 4 change workflows and 33 short concept notes. It also reads
configuration you paste: it explains a line (`ncs what`) and writes the commands that remove it (`ncs undo`).
Everything works offline, in any terminal, also over SSH.

It is an inventory of the commands you don't use every day: 207 of them are marked ◆ ("gem"), so you can look at
them on purpose before you forget them.

**[Quick start](#quick-start)**: install and the everyday how-tos.
**[Reference](#reference)**: every command, option, key, file format and rule in detail.

---

## Quick start

### Install

```bash
git clone <netcheat repo URL from our GitLab> && cd netcheat
pip install -e .
```

Python 3.9 or newer. Keep the `-e` (editable install): a `git pull` then updates your cheatsheet immediately, and
`ncs add` and `ncs build-md` write into this checkout. More: [Install details](#install-details).

### Turn on tab completion

Add one line to `~/.zshrc` (or `~/.bashrc`) and open a new terminal:

```bash
eval "$(ncs completion zsh)"     # bash: eval "$(ncs completion bash)"
```

Now `ncs -t <Tab>`, `ncs export <Tab>` or `ncs adja<Tab>` complete. More: [Tab completion](#tab-completion).

### How to look around

```bash
ncs
```

Opens the full-screen browser: favourites, recent entries, gems, topics, flows and concepts on the left, a live
filter on top (`/`), details on the right. `f` stars an entry, `c` copies, `q` quits. More: [Browser](#browser).

### How to find a command

```bash
ncs isid                 # every command about I-SIDs (hyphens don't matter: also finds "i-sid")
ncs show isis adj        # several words: all must match, and words can be cut short
ncs lacp -k config       # only configuration commands
ncs nick-name -d         # with examples, notes and the link to the official docs
```

More: [Search](#search) and [Reading the output](#reading-the-output).

### How to cut long output down on the switch

```bash
ncs -t output-filters    # | include, | exclude, | begin, | count, | head, | tail, field/header, regex
ncs -t srx-output-filters
ncs grep                 # the overview: patterns, quoting, what is and isn't documented
```

For example `show running-config | include "radius server host"`, `show running-config | exclude "^#"` (the config
without comment lines) or `show vlan basic | include byPort field 3 header 6` (one column only, header kept).
More: [Output filters](#output-filters).

### How to understand a line someone typed or configured

```bash
ncs what sh isis adj
ncs what radius server host 10.0.0.50 key x used-by eapol
ncs what < config-snippet.txt
```

Finds the cheatsheet entry for a command or configuration line (abbreviations work, like on the switch) and, for
configuration, the command that removes it. More: [Explain a line](#explain-a-line-ncs-what).

### How to remove configuration cleanly

```bash
ncs undo                                 # paste the lines, then Ctrl-D
ssh sw1 "show running-config module radius" | ncs undo
```

Prints the `no` commands in a safe order, separately the ones to check first (they could lock you out), and the
lines it has no rule for. It only prints; you review and paste. More: [Remove configuration](#remove-configuration-ncs-undo).

### How to replace RADIUS, SNMP, syslog, NTP, DNS or admin logins

```bash
ncs radius-replace                                   # the change workflow, step by step
ncs radius-replace --set new_radius=10.20.0.50       # ... with your own values filled in
ncs export radius-replace --set new_radius=10.20.0.50 > plan.txt    # for the change ticket, with rollback
```

More: [Change workflows](#change-workflows) and [Export a flow](#export-a-flow-ncs-export).

### How to troubleshoot a problem

```bash
ncs fix the access point does not come up on an autosense port
ncs fix phone works but the pc behind it does not
```

You get the best-matching troubleshooting flow step by step, plus other flows worth checking, helpful commands and
background concepts. To open a flow yourself: `ncs list flows`, then `ncs vist-smlt-problem`.
More: [Problem matching](#problem-matching-ncs-fix) and [Troubleshooting flows](#troubleshooting-flows).

### How to only see commands your switches have

```bash
export NCS_RELEASE=9.4.1         # in ~/.zshrc or ~/.bashrc
```

Fabric Engine commands that came after that release are hidden everywhere. More: [Release filter](#release-filter).

### How to rediscover forgotten commands

```bash
ncs tip                  # a random gem, with details
ncs -r -t spbm-isis      # all gems of one topic
ncs -s 9.4               # commands added in Fabric Engine 9.4 or later
```

### How to understand a term

```bash
ncs nickname             # the concept, then the commands about it
ncs list concepts        # all concepts
```

### How to add a command you use

```bash
ncs add
```

It asks for the fields and appends the entry to a topic file. Then check and share it:
`pip install -e ".[dev]" && pytest && ncs build-md`, then open a merge request.
More: [Adding and editing content](#adding-and-editing-content).

### How to read it without the CLI

Everything is also available as Markdown, browsable on GitLab: [docs/cheatsheet/README.md](docs/cheatsheet/README.md).

---

## Reference

Back to the [Quick start](#quick-start).

- [Install details](#install-details)
- [Commands overview](#commands-overview)
- [Search](#search)
- [Reading the output](#reading-the-output)
- [Browser](#browser)
- [Favourites and recent entries](#favourites-and-recent-entries)
- [Output filters](#output-filters)
- [Explain a line (ncs what)](#explain-a-line-ncs-what)
- [Remove configuration (ncs undo)](#remove-configuration-ncs-undo)
- [Problem matching (ncs fix)](#problem-matching-ncs-fix)
- [Troubleshooting flows](#troubleshooting-flows)
- [Change workflows](#change-workflows)
- [Values in flows](#values-in-flows)
- [Export a flow (ncs export)](#export-a-flow-ncs-export)
- [Concepts](#concepts)
- [Release filter](#release-filter)
- [Topics](#topics)
- [Tab completion](#tab-completion)
- [Adding and editing content](#adding-and-editing-content)
- [Exit codes and environment](#exit-codes-and-environment)
- [Moving the repository](#moving-the-repository)
- [Sources and versions](#sources-and-versions)

### Install details

- Requires Python 3.9 or newer. Dependencies (installed by pip): `rich`, `PyYAML` and `textual` (only used by the
  browser).
- Editable install (`pip install -e .`): the tool reads its data straight from `src/netcheat/data/` in your checkout,
  so `git pull` is enough to update. `ncs add` and `ncs build-md` write into the same checkout. With a normal
  `pip install .` they would write into the installed package instead.
- Development extras: `pip install -e ".[dev]"` adds `pytest`.

### Commands overview

| Command | What it does | Options |
|---|---|---|
| `ncs` | the browser on a terminal; the topic overview when piped | |
| `ncs <words>` / `ncs search <words>` | search commands; an exact flow id or concept name opens it | see [Search](#search) |
| `ncs browse [words]` | the browser, with the filter prefilled | see [Browser](#browser) |
| `ncs what [line]` | explain a command or configuration line; several lines from stdin | `-d` |
| `ncs undo [file]` | the commands that remove configuration lines (file or stdin) | `--plain` |
| `ncs fix <problem>` | match a problem description to flows, commands and concepts | `-p fe\|srx` |
| `ncs export <flow>` | a flow as a plain-text or Markdown document, with rollback | `--md`, `--set`, `--step N`, `--commands` |
| `ncs list [section]` | `topics` (default), `flows`, `concepts`, `favourites` or `recent` | |
| `ncs tip` | a random gem with details | `-p fe\|srx` |
| `ncs add` | add a command interactively | |
| `ncs build-md` | regenerate the Markdown in `docs/cheatsheet/` | `-o <dir>` for another folder |
| `ncs completion bash\|zsh` | print the tab-completion script | |
| `ncs --version` / `ncs -h` | version and credit / help (`ncs <command> -h` for one command) | |

Every lookup command (`search`, `browse`, `what`, `undo`, `fix`, `list`, `tip`) also takes `-R <release>`, see
[Release filter](#release-filter). Platform values for `-p`: `fe` (also `voss`, `fabric-engine`) and `srx` (also
`junos`, `junos-srx`).

### Search

| Option | Meaning |
|---|---|
| `-p fe \| srx` | only one platform |
| `-t <topic>` | only one topic, e.g. `spbm-isis` (see [Topics](#topics)) |
| `-k show \| config \| action \| clear` | only one type of command |
| `-r` | only rarely used gems |
| `-s <version>` | only commands added in this Fabric Engine version or later, e.g. `-s 9.3` |
| `-d` | details: examples, notes, cautions and the link to the official docs |
| `-n <N>` | show at most N results |
| `--set name=value` | when the words are a flow id: your values for the flow, see [Values in flows](#values-in-flows) |

How matching works:

- If the words are exactly a flow id (`ncs radius-replace`), the flow opens. If they are exactly a concept name or
  one of its other names (`ncs nickname`, `ncs virtual ist`), the concept is shown first, then the matching commands.
- Case, hyphens and punctuation are ignored: `isid` finds `i-sid`, `unicast-fib` finds `ip-unicast-fib`, and a pasted
  command such as `show isis adjacencies [verbose]` finds itself.
- Every word is a prefix (`adj` finds `adjacencies`), and all words must match.
- The command text counts most, then tags, the description, the topic and finally notes, examples and the Cisco
  equivalent. A match of the whole phrase in the command ranks first; on ties, show commands and shorter commands
  come first.
- One or two results are shown with details automatically. If nothing matches, `ncs` suggests close spellings.
- Under the results, `ncs` points to matching flows and concepts (respecting `-p`).

### Reading the output

```
» show isis adjacencies [verbose]
  IS-IS neighbors on all NNIs. Every fabric link should show state UP.
  spbm-isis · User EXEC · ≈ Cisco: show isis neighbors
```

The first line is the command, then what it does, then topic, CLI mode and the closest Cisco equivalent (if any).

| Icon | Meaning |
|---|---|
| `»` `✎` `►` `↺` | show / config / action / clear command |
| `◆` | rarely used gem, worth remembering |
| `▲` | caution: traffic impact or risky, read the note with `-d` |
| `↑ 9.4` | added in this Fabric Engine release; older releases do not have it |
| `✕ removed in 9.4` | no longer available from this release |
| `≈ Cisco:` | the closest Cisco equivalent, as an orientation aid |
| `↗` | link to the official documentation |
| `☰` / `⇄` | troubleshooting flow / change workflow |
| `◇` | concept |
| `★` / `◷` | favourite / recent entry |

Command syntax follows the Extreme docs: `<value>` is a placeholder, `[...]` is optional, `{a | b}` is a choice.
Port lists accept `1/5`, `1/1-1/12`, `1/1,1/5` and `1/all`. Icons are plain Unicode symbols, so they work in every
terminal font.

### Browser

`ncs` (or `ncs browse [words]`, which prefills the filter) opens a full-screen browser. It runs in any terminal,
also over SSH.

| Area | Content |
|---|---|
| left | All commands, ★ Favourites, ◷ Recent, Gems, the topics per platform, troubleshooting flows, change workflows, concepts |
| middle | the entries of the selected area, narrowed live by the filter |
| right | details of the highlighted entry: the same content as `ncs ... -d`, a flow or a concept |

| Key | Action |
|---|---|
| arrow keys, mouse | move around; the middle list follows the selection on the left |
| Enter | on the left: jump into the list; in the list: remember the entry as recent; in the filter: back to the list |
| `/` | focus the filter and type words (same rules as [Search](#search)) |
| Esc | leave the filter |
| `g` | toggle "gems only" (command lists) |
| `f` | star or unstar the highlighted entry (see [Favourites](#favourites-and-recent-entries)) |
| `c` | copy the highlighted command (for a flow its id, for a concept its term) |
| `1` to `9` | on a flow: copy all commands of that step, with your values filled in |
| `v` | on a flow: edit its values as `name=value name=value`, Enter applies (see [Values in flows](#values-in-flows)) |
| `q` | quit |

Values set with `v` stay for the session and apply to every flow that uses the same name (e.g. `port`).

Copying uses the OSC 52 terminal sequence, so it also works over SSH in most terminals (iTerm2, Windows Terminal,
kitty, WezTerm, tmux with clipboard enabled), but not in macOS Terminal.app. Without it, use the plain CLI and copy
from its output, e.g. `ncs export radius-replace --step 5`.

### Favourites and recent entries

- **Favourites:** `f` in the browser stars the highlighted command, flow or concept. Starred entries show ★ in every
  list and are collected under ★ Favourites. `ncs list favourites` prints them.
- **Recent:** the last 30 entries you opened: selected (Enter) or copied in the browser, and flows, concepts and
  `ncs what` matches opened from the CLI. Newest first, under ◷ Recent and in `ncs list recent`.
- Both are personal and stored outside the repository, in `~/.local/share/netcheat/state.json` (or
  `$XDG_DATA_HOME/netcheat/state.json`; `NETCHEAT_STATE=<file>` sets another file). Entries are kept by command text,
  flow id or concept name; an entry that no longer exists is skipped. A missing or damaged file is simply empty.

### Output filters

A pipe after a show command filters its output on the switch. The topics `output-filters` (Fabric Engine) and
`srx-output-filters` (Junos) list every filter with examples; the concepts `Output filters (pipe)` and `Junos pipe`
(`ncs grep`) sum up the rules.

| Fabric Engine | Junos | Does |
|---|---|---|
| `\| include <pattern>` | `\| match <pattern>` | only lines that match |
| `\| exclude <pattern>` | `\| except <pattern>` | hide lines that match |
| `\| begin <pattern>` | `\| find <pattern>` | start at the first match |
| `\| count` | `\| count` | count the lines |
| `\| head [<n>]` / `\| tail [<n>]` | `\| last <n>` | first / last lines |
| `\| no-more` | `\| no-more` | no paging |
| | `\| save <file>`, `\| refresh [<s>]`, `\| compare rollback <n>` | save, repeat, diff |

- The pattern is a regular expression; quote it when it contains spaces. Fabric Engine matches case-sensitively
  unless you add `ignore-case`, and `field <n>` / `header <n>` match one column and keep the table header.
- Junos documents `a|b` (either term) and filters in a row. Extreme documents neither, so try
  `| include "radius|snmp"` and `| include x | count` once on your release before relying on them.

`ncs what` explains a whole piped line, e.g. `ncs what 'show runn | inc "radius|snmp" | count'`.

### Explain a line (ncs what)

`ncs what <line>` finds the cheatsheet entry a command or configuration line belongs to:

```
$ ncs what snmp-server host 10.0.0.80 v2c readview
snmp-server host 10.0.0.80 v2c readview
  ✎ snmp-server host <ip> [port <port>] {v2c <secname> | v3 {...} <user>} [inform] [filter <profile>]
    Add a trap/inform receiver. v2c takes the community's secname (not the string), v3 takes the v3 user.
    ...
  Remove with: no snmp-server host 10.0.0.80 v2c readview
```

- The line is matched against the syntax of every entry: keywords exactly or abbreviated to two letters or more
  (`sh isis adj`), `<values>` as any value, `[options]` in any order. The entry with the most matching keywords wins.
- `no ...` and `default ...` lines find the entry they remove or reset, if there is no entry for the `no` form itself.
- If only the beginning of the line matches, the closest entry is shown and marked as such. If nothing matches,
  related commands are suggested.
- For configuration with an [undo rule](#remove-configuration-ncs-undo), `Remove with:` shows the removal command.
- Output filters after the command (`| include ...`, `| match ...`) are explained one by one, for the platform of the
  command. A `|` inside a pattern (`"radius|snmp"`) stays part of the pattern. Quote a piped line for the shell:
  `ncs what 'show running-config | include radius'`.
- Without a line, `ncs what` reads several lines from stdin (paste, then Ctrl-D, or pipe a file) and explains each
  one briefly; `-d` gives full details for all of them. Prompts, comments and pager lines are skipped.

### Remove configuration (ncs undo)

`ncs undo [file]` reads configuration lines (a file, a pipe, or a paste ended with Ctrl-D) and prints:

1. **Removal commands, in this order**: a plain block, ready to paste. The order is the reverse of the
   configuration, because `show running-config` lists what a line depends on before the line itself (servers before
   the global `enable`, hosts before communities). Lines of the same object (several `syslog host 1 ...` lines) give
   one removal.
2. **Check before running**: removals that could hurt (e.g. `no ssh` ends your own SSH session) and manual steps,
   each with a note. They are never in the block above. Example: a community line can't be removed from the
   configuration alone, because the switch masks the string; the note says to look up its index.
3. **No rule for these lines**: everything it does not know, including every line inside an `interface` or
   `router` block. Nothing is dropped silently.

`--plain` prints only the block of removal commands, for piping. The tool never connects to a switch: review the
output, paste it yourself, check the result, then save.

Covered: global management configuration: RADIUS (servers per `used-by`, CoA clients, global settings), TACACS+,
local users, SSH, banners, SNMP (communities, v3 users, groups, views, trap hosts, notify filters, name, contact,
location), syslog, NTP, DNS, and `eapol enable`. Data-plane configuration (VLANs, I-SIDs, IS-IS, MLT, interfaces) is
not, on purpose: there, a wrong order means an outage.

The rules are written from the 9.4 command syntax and Extreme KB articles about how `show running-config` prints
these lines. They accept quoted and unquoted values and options in any order, and the tests check every rule. They
have not been checked against output from our own switches yet: if a line ends up under "No rule", that's the sign
to send the line in so the rule can be fixed.

### Problem matching (ncs fix)

`ncs fix <problem>` reads a free-text description (quotes are optional) and shows:

1. **Understood:** the key words it recognized, so you can see how it read your description.
2. **The best-matching flow**, step by step, plus up to 3 more flows under "Also check".
3. **Helpful commands** (up to 6) and **background concepts** (up to 3).

How it works, all offline and deterministic:

- Phrases from [`synonyms.yaml`](src/netcheat/data/synonyms.yaml) are recognized first ("access point", "no ip",
  "flapping"). A recognized group searches with all its single-word entries, e.g. "access point" also searches
  ap, wap, wifi and fa. Multi-word phrases only serve to recognize the group, so their generic words ("up", "no")
  don't match everything.
- Filler words ("the", "does", "not", "keeps", ...) are dropped. Other words count on their own, lightly stemmed
  ("joining" also finds "join"). Single words of four or more letters also match as a prefix ("flap" finds
  "flapping"), shorter ones only exactly.
- Flows are ranked by how many aspects of the problem they cover, then by where they match: their `symptoms` count
  most, then id, title, tags and summary. Commands and concepts must cover two aspects when the description has two.
- Change wording works too: `ncs fix remove the old radius servers` finds the change workflow.
- `-p fe|srx` limits everything to one platform.

If `ncs fix` misreads your wording, teach it: add the words to a group in `synonyms.yaml`, or add a typical phrasing
to the `symptoms` of the right flow (see [Adding and editing content](#adding-and-editing-content)).

### Troubleshooting flows

`ncs list flows` lists all flows; `ncs <id>` opens one. Search words also find flows by title, tags, symptoms and
summary. Each flow is an ordered list of steps with example commands and what to look for.

| Flow id | For |
|---|---|
| `client-no-connectivity` | a client has no network or gets no IP |
| `nac-auth-failure` | a client is not authenticated or lands in the wrong VLAN/I-SID |
| `isis-adjacency-down` | an IS-IS adjacency on an NNI does not come up |
| `l2vsn-not-working` | the same VLAN at two sites cannot talk |
| `l3vsn-route-missing` | a VRF route is missing on another BEB |
| `vist-smlt-problem` | vIST down or SMLT dual-homing not working |
| `autosense-onboarding` | a new switch or AP on an Auto-sense port does not onboard |
| `loop-broadcast-storm` | a suspected loop or broadcast storm |
| `port-errors-flapping` | a port flaps or counts errors |
| `macsec-link-down` | a MACsec link passes no traffic |
| `switch-slow-high-cpu` | the switch is slow or has a high CPU |
| `multicast-not-working` | a multicast stream does not reach the receivers |
| `srx-routed-traffic-dropped` | the SRX routes, but traffic does not pass |
| `srx-unhealthy-or-failover` | the SRX failed over, is slow or shows alarms |

### Change workflows

Change workflows (⇄) are flows for configuration changes instead of faults: remove, replace or re-add a feature
without guessing the `no` syntax and without locking yourself out. They all go the same way: see what is set, set a
safety net (`reset -in 30` before touching admin logins), add the new config, test, remove the old pieces, verify,
save and cancel the safety net. Inside a step, » marks show commands, ✎ config commands and ► actions. ▲ marks a
step with a risk, e.g. losing your own login.

| Flow id | For |
|---|---|
| `radius-replace` | replace or remove RADIUS servers for NAC (eapol) and admin login (cli), and the CoA client |
| `snmp-replace` | replace or remove communities, v3 users, groups, views and trap receivers |
| `syslog-ntp-dns-replace` | replace or remove syslog, NTP and DNS servers |
| `admin-login-change` | replace TACACS+ or RADIUS login servers, clean up local users, SSH and telnet |

The single `no` commands with their exact syntax are in the topics `mgmt-access` and `mgmt-services`
(`ncs -t mgmt-services no`), and `ncs undo` writes them from your own configuration.

### Values in flows

The example values of a flow (ports, VLANs, VRFs, server addresses, user names) are named, and the flow shows them on
its `Values:` line, e.g. `old_radius=10.0.0.50 · new_radius=10.0.1.50 · port=1/5`. Replace them with your own:

- CLI: `ncs radius-replace --set new_radius=10.20.0.50 --set port=2/7` (also with `ncs export`). A name the flow
  does not use is an error that lists the names it has.
- Browser: `v` on a flow, then edit `name=value` pairs. The values apply to every flow with the same name, until you
  quit. The step copy keys (`1` to `9`) copy the filled-in commands.

Secrets (`<secret>`) are never filled in; type them on the switch.

### Export a flow (ncs export)

`ncs export <flow-id>` prints a flow as a document for a change ticket:

| Option | Output |
|---|---|
| (none) | plain text: title, summary, values, numbered steps with commands, checks and cautions |
| `--md` | the same as Markdown |
| `--set name=value` | your values filled in (repeatable) |
| `--step N` | only the commands of step N, one per line, ready to paste |
| `--commands` | only the commands of all steps, one per line |

Change workflows get a **Rollback** section: the removal commands for everything the plan adds, generated with the
`ncs undo` rules, in reverse order. What the plan removes can only be restored from the original lines, so save
`show running-config` before step 1. Risky removals (like `no ssh`) are listed below the block, not in it.

### Concepts

`ncs list concepts` lists all concepts; `ncs <name>` shows one with a short explanation, then the related commands.
They cover the building blocks: SPBM, BEB/BCB, B-VLAN, nickname, system ID, I-SID, UNI/NNI, L2/L3 VSN, IP shortcuts,
CLIP, vIST/SMLT, RSMLT, DvR, Anycast Gateway, Auto-sense, Fabric Attach, Zero Touch Fabric, EAP/NEAP, guest and
fail-open I-SIDs, CoA, MACsec, SLPP, CFM, Segmented VRF, IGMP querier, DHCP snooping/DAI/IP Source Guard, output
filters, and for the SRX flow mode, the commit model, routing instances, chassis cluster and the Junos pipe.

### Release filter

`-R <release>` (or `--release`) on any lookup command, or `NCS_RELEASE=<release>` in your shell profile, hides the
Fabric Engine commands that do not exist on that release: commands added later (`since`) and commands removed in or
before it (`removed`). Juniper commands are not affected. `ncs list` shows the release in its summary line. The
option wins over the environment variable, so `ncs isid -R 9.4.2` checks a newer release once.

### Topics

Use the id with `-t`. `ncs list` shows the current counts.

| Topic id | Platform | Title | Commands |
|---|---|---|---|
| `auto-sense-fa` | Extreme Fabric Engine | Auto-sense, Fabric Attach and Zero Touch | 22 |
| `dvr-anycast` | Extreme Fabric Engine | DvR and Anycast Gateway | 18 |
| `edge-security` | Extreme Fabric Engine | Edge Security and Storm Control | 11 |
| `l2vsn-isid` | Extreme Fabric Engine | L2 VSN and I-SID Services | 15 |
| `l3vsn-routing` | Extreme Fabric Engine | L3 VSN, VRF and Routing | 33 |
| `macsec` | Extreme Fabric Engine | MACsec | 13 |
| `mgmt-access` | Extreme Fabric Engine | Management Access (RADIUS, TACACS+, Users, SSH) | 20 |
| `mgmt-services` | Extreme Fabric Engine | Management Services (SNMP, Syslog, NTP, DNS) | 25 |
| `mlt-smlt-vist` | Extreme Fabric Engine | MLT, SMLT, vIST and LACP | 18 |
| `multicast` | Extreme Fabric Engine | IP Multicast and IGMP | 14 |
| `nac-eap-radius` | Extreme Fabric Engine | NAC, EAP/NEAP and RADIUS | 25 |
| `output-filters` | Extreme Fabric Engine | Output Filters and Paging | 9 |
| `ports` | Extreme Fabric Engine | Ports, VLANs and Loop Protection | 48 |
| `qos-monitoring` | Extreme Fabric Engine | QoS, Filters and Traffic Monitoring | 7 |
| `spbm-isis` | Extreme Fabric Engine | SPBM, IS-IS and Fabric OAM | 40 |
| `system` | Extreme Fabric Engine | System, CLI and Files | 50 |
| `srx-output-filters` | Juniper SRX | Juniper SRX Output Filters | 9 |
| `srx-routing` | Juniper SRX | Juniper SRX Routing, Interfaces and Traffic | 27 |
| `srx-system` | Juniper SRX | Juniper SRX System Health and Chassis Cluster | 16 |

### Tab completion

`ncs completion zsh` (or `bash`) prints a small shell function; `eval` it from your shell profile. It completes:

| After | Candidates |
|---|---|
| `ncs` | subcommands; with a first letter also search words, flow ids and concept names |
| `-t` / `-p` / `-k` / `-s` / `-R` | topic ids / platforms / command kinds / versions that appear in the data |
| `-` | the options of the current subcommand |
| `ncs export` / `ncs list` / `ncs completion` | flow ids / list sections / `bash`, `zsh` |
| `ncs what` words, `ncs fix` words | command words / the vocabulary `ncs fix` understands, once a letter is typed |

On each Tab the shell runs `ncs __complete <position> <words...>`. Options and choices answer without reading the
data; data-based candidates take less than 0.1 s. Use the short option form for values (`-t macsec`); `--topic=...`
does not complete. The zsh script runs `compinit` if your profile has not done it already.

### Adding and editing content

All content lives in YAML files under `src/netcheat/data/`:

```
fabric-engine/<topic>.yaml   one topic per file; the file name is the topic id for -t
junos-srx/<topic>.yaml
flows.yaml                   troubleshooting flows (with typical symptoms for ncs fix)
changes.yaml                 change workflows (same format as flows.yaml)
concepts.yaml                concept explanations
synonyms.yaml                words that mean the same thing, for ncs fix
```

`ncs add` asks for the fields and appends a command to a topic file (it keeps comments and layout, and restores the
file if the result does not load). You can also edit the files by hand.

**A command** (in a topic file, under `commands:`):

```yaml
  - cmd: show isis spbm nick-name [home | remote]   # required: the command, with <placeholders> and [optional] parts
    desc: Every fabric node with nickname, system-id and hostname.   # required
    kind: show                 # required: show | config | action | clear
    mode: User EXEC            # required: CLI mode (Fabric Engine) or operational / configuration (Junos)
    tags: [nickname, fabric, inventory]   # extra search words
    example: |                 # real-world example lines
      show isis spbm nick-name | include SW-ACCESS
    notes: >                   # background and pitfalls
      Look up a nickname from another output and get the switch name.
    caution: ...               # traffic impact or risk, shows ▲
    cisco: ...                 # the closest Cisco equivalent
    since: "9.3"               # the release that introduced the command (quoted!)
    removed: "9.4"             # the release that removed it
    rare: true                 # marks a gem ◆
    undo:                      # how ncs undo removes this configuration (config commands only)
      - match: "syslog host <id> ..."     # the line as show running-config prints it
        remove: "no syslog host <id>"     # filled from the <names> captured by match
        note: ...              # optional: puts the removal under "check before running"
    ref: https://documentation.extremenetworks.com/...   # link to the official docs
```

The `cmd` syntax is also what `ncs what` matches lines against: `<value>`, `[optional]` (options in any order),
`{a | b}`, two related commands as `a / b`, and annotations in round brackets, such as `(interface)`, which are
ignored.

**Undo rules:** `match` uses the same notation plus `...` for "any values here". Write it for the line as `show
running-config` prints it, keep only what identifies the object, and put `...` where keys, options and their order can
vary. A rule without `remove` is a manual step and needs a `note`. When several rules match a line, the one with the
most keywords wins; the tests build a sample line from every rule and check that the rule wins for it.

A topic file starts with `title:` (required) and `description:`, and ends with `commands:`.

**A flow** (in `flows.yaml` or `changes.yaml`, under `flows:`):

```yaml
  - id: client-no-connectivity          # required, unique, used by `ncs <id>`
    title: Client has no network connectivity   # required
    platform: fabric-engine             # required: fabric-engine | junos-srx
    tags: [client, dhcp]
    symptoms:                           # typical phrasings, used by ncs fix and flow search
      - pc gets no ip address
    summary: >                          # required
      Work from the bottom up ...
    values: {port: 1/5, vlan: 100}      # defaults of the {name} placeholders below
    steps:                              # required
      - title: Is the port up?          # required
        cmds: ["show interfaces gigabitEthernet name {port}"]
        look_for: Oper status up, no rising CRC errors.
        caution: ...                    # a risk in this step, shows ▲
```

Write every example value as `{name}` (lowercase, digits and `_`) and give its default under `values`; it is
replaced in titles, summary, commands, `look_for` and `caution`. Every placeholder needs a default and every default
must be used. Inside `[...]` lists, a `{name}` needs the whole item quoted. A change workflow (in `changes.yaml`) has
exactly the same fields; the file decides the kind.

**A concept** (in `concepts.yaml`, under `concepts:`): `term`, `text` and `platform` are required; `aka` (other
names) and `see` (related commands, each the exact `cmd` text of an existing command) are optional.

**A synonym group** (in `synonyms.yaml`, under `groups:`): a list of words and phrases that mean the same thing,
e.g. `- [ap, access point, wap, wifi, wireless, fa]`. Avoid very general words (they would match almost every problem).

Rules:

- Keep `commands:` as the last key of a topic file, because `ncs add` appends to it.
- Quote version numbers (`"9.4"`) and words YAML reads specially (`null`, `yes`, `no`, `on`, `off`). Whole numbers
  such as model numbers (`tags: [5520]`) or VLAN ids (`values: {vlan: 100}`) are fine without quotes.
- Mistakes stop the tool with the file and the entry, e.g.
  `Data error: ports.yaml #12 (speed ...): unknown field(s): colour`.
- The tests check, among other things, that no command appears twice per platform and CLI mode, that every concept
  reference exists, that every Fabric Engine command links to the official docs, that every undo rule wins for its
  own line, and that `ncs fix` still finds the right flow for a set of example problems.

After a change, run the checks, regenerate the Markdown and open a merge request:

```bash
pip install -e ".[dev]"
pytest
ncs build-md
```

`ncs build-md` rewrites `docs/cheatsheet/` (one page per topic, plus troubleshooting flows, change workflows with
their rollback, concepts and an index) and removes generated pages of topics that no longer exist. Hand-written files
in that folder are left alone. Flows appear there with their default values filled in.

### Exit codes and environment

| Exit code | Meaning |
|---|---|
| 0 | success |
| 1 | nothing matched or found (search, `what`, `undo`, `fix`, `tip`) |
| 2 | invalid option or input (unknown flow or value, missing file), data error (the message names the file and entry), or `ncs add` did not save |

| Variable | Effect |
|---|---|
| `NCS_RELEASE=<release>` | default for `-R`, see [Release filter](#release-filter) |
| `NETCHEAT_STATE=<file>` | where favourites and recent entries are stored |
| `NETCHEAT_DATA=<dir>` | read the data from another folder with the same layout, e.g. to try out changes without touching the checkout |

### Moving the repository

To move the project to another Git server (or a machine without access to this one), pack it into a single file:

```bash
python scripts/make_bootstrap.py          # writes dist/netcheat-bootstrap.py
```

The generated script contains every file of the working tree (tracked and new, not ignored) with a SHA-256 checksum,
and needs only Python 3.9+. Copy it over and run:

```bash
python netcheat-bootstrap.py netcheat --git   # recreate the files, git init and commit
cd netcheat && git remote add origin <url> && git push -u origin main
```

It refuses to write into a non-empty folder and stops if a file was damaged in transfer. `--git` needs Git 2.28 or newer.

### Sources and versions

The Fabric Engine content is checked against the official **Fabric Engine 9.4 Command Reference and User Guide**, and
the release notes for 9.2, 9.3, 9.4, 9.4.1 and 9.4.2. Each command links to its reference page. The `since` versions
come from comparing the 9.1, 9.2, 9.3 and 9.4 command references; commands without `since` exist in 9.1 already.
The output filters come from the 9.4 User Guide pages "GREP with CLI show command" and "Use GREP CLI Show Command
Filters", and from Juniper's "| (pipe)" reference and "Filtering Operational Command Output".
How `show running-config` prints management configuration (quoted names, masked communities stored outside the
running config) comes from Extreme KB articles 000067212, 000078215 and 000115014. Community forum threads were used
only as an extra reference; the few hints taken from them say so in their notes.

Nothing here has been tested on our hardware, so try unfamiliar configuration commands and generated removal
commands in the lab first.
