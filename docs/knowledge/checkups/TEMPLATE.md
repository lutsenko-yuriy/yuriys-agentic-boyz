# CHK-YYYY-MM-DD-<tier>: <one-line summary>

## Run info

- **Tier:** light | heavy
- **Date:** YYYY-MM-DD
- **Period covered:** YYYY-MM (light) or YYYY-Qn (heavy)
- **Dimensions walked:** <list — see `skills/manage/checkup/resources/light-dimensions.md` or `heavy-dimensions.md`>

## Findings

### <Dimension name>

- **Finding:** <what was found>
- **Debt quadrant:** deliberate/inadvertent × reckless/prudent (see [Fowler](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html))
- **Disposition:** fixed inline (commit `<sha>`) | deferred — see ledger Open findings, deadline `YYYY-MM-DD`
- **Graduation candidate:** yes/no — if yes, note the mechanical check this dimension could graduate into

<repeat per finding; omit dimensions with no findings>

## Ledger updates

- Cadence & due status: `<Tier>` → Last run `YYYY-MM-DD`, Period covered `<period>`
- Open findings added: `<IDs, or none>`
- Resolved findings closed: `<IDs, or none>`
