# netcheat

`ncs` is a command cheatsheet for the terminal. It covers **Extreme Fabric Engine (VOSS)** in depth and the
**Juniper SRX** troubleshooting basics: 361 commands with descriptions, examples, notes, Cisco equivalents and links to
the official documentation, plus 14 step-by-step troubleshooting flows and 31 short concept notes. Everything works offline.

It is an inventory of the commands you don't use every day: 187 of them are marked ◆ ("gem"), so you can look at
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

Now `ncs -t <Tab>`, `ncs flow <Tab>` or `ncs adja<Tab>` complete. More: [Tab completion](#tab-completion).

### How to find a command

```bash
ncs isid                 # every command about I-SIDs (hyphens don't matter: also finds "i-sid")
ncs show isis adj        # several words: all must match, and words can be cut short
ncs lacp -k config       # only configuration commands
ncs nick-name -d         # with examples, notes and the link to the official docs
```

More: [Search](#search) and [Reading the output](#reading-the-output).

### How to look around when you only have a broad idea

```bash
ncs browse
```

Pick a topic, "Gems", "Troubleshooting flows" or "Concepts" on the left, type `/` to filter, `c` to copy the
highlighted command, `q` to quit. More: [Browser](#browser).

### How to troubleshoot a problem

Describe it in your own words:

```bash
ncs fix the access point does not come up on an autosense port
ncs fix phone works but the pc behind it does not
```

You get the best-matching troubleshooting flow step by step, plus other flows worth checking, helpful commands and
background concepts. To pick a flow yourself: `ncs flow` lists them, `ncs flow vist-smlt-problem` opens one.
More: [Problem matching](#problem-matching-ncs-fix) and [Troubleshooting flows](#troubleshooting-flows).

### How to rediscover forgotten commands

```bash
ncs tip                  # a random gem, with details
ncs -r -t spbm-isis      # all gems of one topic
ncs -s 9.4               # commands added in Fabric Engine 9.4 or later
```

More: [Search options](#search).

### How to understand a term

```bash
ncs concept nickname     # what a nickname is, and which commands show it
ncs concept              # list all concepts
```

More: [Concepts](#concepts).

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
- [Problem matching (ncs fix)](#problem-matching-ncs-fix)
- [Troubleshooting flows](#troubleshooting-flows)
- [Concepts](#concepts)
- [Topics](#topics)
- [Tab completion](#tab-completion)
- [Adding and editing content](#adding-and-editing-content)
- [Exit codes and environment](#exit-codes-and-environment)
- [Sources and versions](#sources-and-versions)

### Install details

- Requires Python 3.9 or newer. Dependencies (installed by pip): `rich`, `PyYAML` and `textual` (only used by
  `ncs browse`).
- Editable install (`pip install -e .`): the tool reads its data straight from `src/netcheat/data/` in your checkout,
  so `git pull` is enough to update. `ncs add` and `ncs build-md` write into the same checkout. With a normal
  `pip install .` they would write into the installed package instead.
- Development extras: `pip install -e ".[dev]"` adds `pytest`.

### Commands overview

| Command | What it does | Options |
|---|---|---|
| `ncs <words>` / `ncs search <words>` | search commands | see [Search](#search) |
| `ncs` (no arguments) / `ncs topics` | overview of all topics with command and gem counts | |
| `ncs browse [words]` | full-screen browser, optionally with the filter prefilled | see [Browser](#browser) |
| `ncs fix <problem>` | match a problem description to flows, commands and concepts | `-p fe\|srx` |
| `ncs flow [id \| words]` | list flows, open one by id, or search them | |
| `ncs concept [words]` | list concepts or show the matching ones | |
| `ncs tip` | a random gem with details | `-p fe\|srx` |
| `ncs add` | add a command interactively | |
| `ncs build-md` | regenerate the Markdown in `docs/cheatsheet/` | `-o <dir>` for another folder |
| `ncs completion bash\|zsh` | print the tab-completion script | |
| `ncs --version` / `ncs -h` | version and credit / help (`ncs <command> -h` for one command) | |

Platform values for `-p`: `fe` (also `voss`, `fabric-engine`) and `srx` (also `junos`, `junos-srx`).

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

How matching works:

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

Command syntax follows the Extreme docs: `<value>` is a placeholder, `[...]` is optional, `{a | b}` is a choice.
Port lists accept `1/5`, `1/1-1/12`, `1/1,1/5` and `1/all`. Icons are plain Unicode symbols, so they work in every
terminal font.

### Browser

`ncs browse [words]` opens a full-screen browser; the optional words prefill the filter.

| Area | Content |
|---|---|
| left | All commands, Gems, the topics per platform, Troubleshooting flows, Concepts |
| middle | the entries of the selected area, narrowed live by the filter |
| right | details of the highlighted entry: the same content as `ncs ... -d`, `ncs flow <id>` or `ncs concept` |

| Key | Action |
|---|---|
| arrow keys, mouse | move around; the middle list follows the selection on the left |
| Enter | on the left: jump into the list; in the filter: back to the list |
| `/` | focus the filter and type words (same rules as [Search](#search)) |
| Esc | leave the filter |
| `g` | toggle "gems only" (command lists) |
| `c` | copy the highlighted command (for a flow its id, for a concept its term) |
| `q` | quit |

Copying uses the OSC 52 terminal sequence, so it also works over SSH in most terminals (iTerm2, Windows Terminal,
kitty, WezTerm, tmux with clipboard enabled), but not in macOS Terminal.app.

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
- `-p fe|srx` limits everything to one platform.

If `ncs fix` misreads your wording, teach it: add the words to a group in `synonyms.yaml`, or add a typical phrasing
to the `symptoms` of the right flow in `flows.yaml` (see [Adding and editing content](#adding-and-editing-content)).

### Troubleshooting flows

`ncs flow` lists all flows; `ncs flow <id>` opens one; other words search titles, tags, symptoms and summaries.
Each flow is an ordered list of steps with example commands and what to look for.
The example values (port 1/5, VLAN 100, I-SID 20100, VRF CORP) are placeholders for your own.

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

### Concepts

`ncs concept` lists all concepts; `ncs concept <words>` shows the matching ones with a short explanation and the
related commands. They cover the building blocks: SPBM, BEB/BCB, B-VLAN, nickname, system ID, I-SID, UNI/NNI,
L2/L3 VSN, IP shortcuts, CLIP, vIST/SMLT, RSMLT, DvR, Anycast Gateway, Auto-sense, Fabric Attach, Zero Touch Fabric,
EAP/NEAP, guest and fail-open I-SIDs, CoA, MACsec, SLPP, CFM, Segmented VRF, IGMP querier, DHCP snooping/DAI/IP Source
Guard, and for the SRX flow mode, the commit model, routing instances and chassis cluster.

### Topics

Use the id with `-t`. `ncs topics` shows the current counts.

| Topic id | Platform | Title | Commands |
|---|---|---|---|
| `auto-sense-fa` | Extreme Fabric Engine | Auto-sense, Fabric Attach and Zero Touch | 22 |
| `dvr-anycast` | Extreme Fabric Engine | DvR and Anycast Gateway | 18 |
| `edge-security` | Extreme Fabric Engine | Edge Security and Storm Control | 11 |
| `l2vsn-isid` | Extreme Fabric Engine | L2 VSN and I-SID Services | 15 |
| `l3vsn-routing` | Extreme Fabric Engine | L3 VSN, VRF and Routing | 33 |
| `macsec` | Extreme Fabric Engine | MACsec | 13 |
| `mlt-smlt-vist` | Extreme Fabric Engine | MLT, SMLT, vIST and LACP | 18 |
| `multicast` | Extreme Fabric Engine | IP Multicast and IGMP | 14 |
| `nac-eap-radius` | Extreme Fabric Engine | NAC, EAP/NEAP and RADIUS | 25 |
| `ports` | Extreme Fabric Engine | Ports, VLANs and Loop Protection | 48 |
| `qos-monitoring` | Extreme Fabric Engine | QoS, Filters and Traffic Monitoring | 7 |
| `spbm-isis` | Extreme Fabric Engine | SPBM, IS-IS and Fabric OAM | 40 |
| `system` | Extreme Fabric Engine | System, CLI and Files | 54 |
| `srx-routing` | Juniper SRX | Juniper SRX Routing, Interfaces and Traffic | 27 |
| `srx-system` | Juniper SRX | Juniper SRX System Health and Chassis Cluster | 16 |

### Tab completion

`ncs completion zsh` (or `bash`) prints a small shell function; `eval` it from your shell profile. It completes:

| After | Candidates |
|---|---|
| `ncs` | subcommands; with a first letter also search words |
| `-t` / `-p` / `-k` / `-s` | topic ids / platforms / command kinds / versions that appear in the data |
| `-` | the options of the current subcommand |
| `ncs flow` / `ncs concept` / `ncs completion` | flow ids / concept words / `bash`, `zsh` |
| search words, `ncs fix` words | command words, or the vocabulary `ncs fix` understands, once a letter is typed |

On each Tab the shell runs `ncs __complete <position> <words...>`. Options and choices answer without reading the
data, in about 0.05 s; data-based candidates take about 0.1 s. Use the short option form for values (`-t macsec`);
`--topic=...` does not complete. The zsh script runs `compinit` if your profile has not done it already.

### Adding and editing content

All content lives in YAML files under `src/netcheat/data/`:

```
fabric-engine/<topic>.yaml   one topic per file; the file name is the topic id for -t
junos-srx/<topic>.yaml
flows.yaml                   troubleshooting flows (with typical symptoms for ncs fix)
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
    ref: https://documentation.extremenetworks.com/...   # link to the official docs
```

A topic file starts with `title:` (required) and `description:`, and ends with `commands:`.

**A flow** (in `flows.yaml`, under `flows:`):

```yaml
  - id: client-no-connectivity          # required, unique, used by `ncs flow <id>`
    title: Client has no network connectivity   # required
    platform: fabric-engine             # required: fabric-engine | junos-srx
    tags: [client, dhcp]
    symptoms:                           # typical phrasings, used by ncs fix and flow search
      - pc gets no ip address
    summary: >                          # required
      Work from the bottom up ...
    steps:                              # required
      - title: Is the port up?          # required
        cmds: [show interfaces gigabitEthernet name 1/5]
        look_for: Oper status up, no rising CRC errors.
```

**A concept** (in `concepts.yaml`, under `concepts:`): `term`, `text` and `platform` are required; `aka` (other
names) and `see` (related commands, each the exact `cmd` text of an existing command) are optional.

**A synonym group** (in `synonyms.yaml`, under `groups:`): a list of words and phrases that mean the same thing,
e.g. `- [ap, access point, wap, wifi, wireless, fa]`. Avoid very general words (they would match almost every problem).

Rules:

- Keep `commands:` as the last key of a topic file, because `ncs add` appends to it.
- Quote version numbers (`"9.4"`) and words YAML reads specially (`null`, `yes`, `no`, `on`, `off`). Whole numbers
  such as model numbers (`tags: [5520]`) are fine without quotes.
- Mistakes stop the tool with the file and the entry, e.g.
  `Data error: ports.yaml #12 (speed ...): unknown field(s): colour`.
- The tests check, among other things, that no command appears twice per platform and CLI mode, that every concept reference exists,
  that every Fabric Engine command links to the official docs, and that `ncs fix` still finds the right flow for a
  set of example problems.

After a change, run the checks, regenerate the Markdown and open a merge request:

```bash
pip install -e ".[dev]"
pytest
ncs build-md
```

`ncs build-md` rewrites `docs/cheatsheet/` (one page per topic, plus flows, concepts and an index) and removes
generated pages of topics that no longer exist. Hand-written files in that folder are left alone.

### Exit codes and environment

| Exit code | Meaning |
|---|---|
| 0 | success |
| 1 | nothing matched (search, `fix`, `flow`, `concept`, `tip`) |
| 2 | invalid option or data error (the message names the file and entry), or `ncs add` did not save |

`NETCHEAT_DATA=<dir>` makes `ncs` read its data from another folder with the same layout, for example to try out
changes without touching the checkout.

### Sources and versions

The Fabric Engine content is checked against the official **Fabric Engine 9.4 Command Reference and User Guide**, and
the release notes for 9.2, 9.3, 9.4, 9.4.1 and 9.4.2. Each command links to its reference page. The `since` versions
come from comparing the 9.1, 9.2, 9.3 and 9.4 command references; commands without `since` exist in 9.1 already.
Community forum threads were used only as an extra reference; the few hints taken from them say so in their notes.

Nothing here has been tested on our hardware, so try unfamiliar configuration commands in the lab first.
Background on the goals and design decisions: [docs/USECASE.md](docs/USECASE.md).

Back to the [Quick start](#quick-start).

---

Provided by **Timmy**, built for the love of the game.
