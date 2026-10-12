# netcheat

`ncs` is a searchable command cheatsheet for the terminal. It covers **Extreme Fabric Engine (VOSS)** in depth and the
**Juniper SRX** basics: about 285 commands with descriptions, examples, notes, Cisco equivalents and links to the
official Extreme documentation. It also has step-by-step troubleshooting flows and short concept notes.

It is meant as an inventory of the commands you don't use every day. Commands like that are marked ◆ ("gem"), so you
can browse them on purpose.

## Install

```bash
git clone <netcheat repo URL from our GitLab> && cd netcheat
pip install -e .
```

Python 3.9 or newer. `-e` (editable) means a `git pull` updates your cheatsheet immediately, without reinstalling.

## Usage

```bash
ncs isid                     # search everything for "isid" (also matches "i-sid")
ncs show isis adj            # several words: all of them must match, words can be prefixes
ncs topics                   # overview of all topics (same as running ncs without arguments)
ncs -t macsec                # every command of one topic
ncs lacp -k config           # only configuration commands
ncs -r -p fe                 # only the rarely used gems on Fabric Engine
ncs -s 9.3                   # commands added in Fabric Engine 9.3 or later
ncs route -p srx -d          # Juniper SRX routing commands with examples and notes
ncs flow                     # list the troubleshooting flows
ncs flow no-connectivity     # step through a flow
ncs concept nickname         # short explanation of a concept
ncs tip                      # a random command you might have forgotten
```

`ncs -h` and `ncs search -h` list all options.

| Option | Meaning |
|---|---|
| `-p fe \| srx` | platform: Fabric Engine or Juniper SRX |
| `-t <topic>` | topic, e.g. `spbm-isis`, `nac-eap-radius` (see `ncs topics`) |
| `-k show \| config \| action \| clear` | type of command |
| `-r` | only rarely used gems |
| `-s <version>` | only commands added in this Fabric Engine version or later |
| `-d` | details: examples, notes, cautions, link to the official docs |
| `-n <N>` | show at most N results |

With one or two results, `ncs` shows the details automatically. If nothing matches, it suggests close spellings.

### Reading the output

```
» show isis adjacencies [verbose]
  IS-IS neighbors on all NNIs. Every fabric link should show state UP.
  spbm-isis · User EXEC · ≈ Cisco: show isis neighbors
```

| Icon | Meaning |
|---|---|
| `»` `✎` `►` `↺` | show / config / action / clear command |
| `◆` | rarely used gem, worth remembering |
| `▲` | caution: traffic impact or risky, read the note (`-d`) |
| `↑ 9.4` | added in this Fabric Engine release (older releases do not have it) |
| `≈ Cisco:` | the closest Cisco equivalent, as an orientation aid |

Placeholders are written as `<value>`, optional parts as `[...]` and choices as `{a | b}`, like in the Extreme docs.

### Without the CLI

The same content as Markdown, browsable on GitLab: [docs/cheatsheet/README.md](docs/cheatsheet/README.md).

## Adding and editing commands

All content lives in YAML files under `src/netcheat/data/`:

```
fabric-engine/<topic>.yaml   one topic per file (the file name is the topic id for -t)
junos-srx/<topic>.yaml
flows.yaml                   troubleshooting flows
concepts.yaml                concept explanations
```

The quickest way to add a command is `ncs add`, which asks for the fields and appends the entry to a topic file. You
can also edit the files by hand. An entry looks like this:

```yaml
  - cmd: show isis spbm nick-name [home | remote]   # the command, with <placeholders> and [optional] parts
    desc: Every fabric node with nickname, system-id and hostname.
    kind: show                 # show | config | action | clear
    mode: User EXEC            # CLI mode (Fabric Engine) or operational / configuration (Junos)
    tags: [nickname, fabric, inventory]   # extra search words
    example: |                 # optional, real-world example lines
      show isis spbm nick-name | include SW-ACCESS
    notes: >                   # optional background, pitfalls
      Look up a nickname from another output and get the switch name.
    caution: ...               # optional, shows ▲
    cisco: ...                 # optional Cisco equivalent
    since: "9.3"               # optional, the release that introduced the command (quoted!)
    removed: "9.4"             # optional, the release that removed it
    rare: true                 # optional, marks a gem ◆
    ref: https://documentation.extremenetworks.com/...   # optional link to the official docs
```

Rules:

- Keep `commands:` as the last key of a topic file (`ncs add` appends to it).
- Quote version numbers (`"9.4"`) and words YAML reads specially (`null`, `yes`, `no`, `on`, `off`).
- Mistakes are reported with the file and the entry, e.g. `Data error: ports.yaml #12 (speed ...): unknown field(s): colour`.

After a change, run the checks and regenerate the Markdown, then open a merge request:

```bash
pip install -e ".[dev]"
pytest
ncs build-md
```

## Sources and versions

The Fabric Engine content is checked against the official **Fabric Engine 9.4 Command Reference and User Guide**, and
the release notes for 9.2, 9.3, 9.4, 9.4.1 and 9.4.2. Each command links to its reference page. Version tags
(`since`) come from comparing the 9.1, 9.2, 9.3 and 9.4 command references. Community forum threads were used only
as an extra reference; the few hints taken from them say so in their notes. Nothing here is tested on our hardware, so try unfamiliar configuration
commands in the lab first. More background: [docs/USECASE.md](docs/USECASE.md).
