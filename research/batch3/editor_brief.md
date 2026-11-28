# Editor brief — batch 2

You are the last reader before the site owner. The texts were researched and
then verified against their cited pages. Your job is reading quality and
internal logic, as a careful human editor would.

For each entry in your input file(s):
- Read the text as a visitor would. Fix Polish grammar, awkward word order,
  unclear references ("ten dom", "on" — who?), and run-on sentences.
- Catch logic slips the verifier can miss (batch 1 had: "nearly four
  centuries" that did not add up, a date that contradicted the next owner, a
  name origin stated as fact when it was a guess). Check dates are in a
  sensible order, counts/durations add up, guesses are marked as guesses
  ("według Chmiela", "Chmiel przypuszcza").
- Past tense for anything Chmiel calls "today" (he wrote 1917–1935).
- Keep it 2–5 sentences. Each sentence must keep ending with its markers
  `[n]` after the full stop. If you merge or split sentences, keep every fact
  with the markers of the source that states it.
- NEVER add a fact, a name, a date or an adjective that is not already in the
  text. You may remove a sentence if it is unclear or contradictory (say why).
- Use `notes` and `verification.removed` for context; you may re-open a
  cited page (`cd /home/user/krakow-building-history && python3
  scripts/library_search.py --page <source-id> <scan>`) if a fix depends on it.

Output: the same list, with your edits, plus per entry
`"editor": {"changes": ["short description of each change", ...]}` (empty
list if none). Skip-objects and dropped ones are copied unchanged. Validate
JSON and the marker rule with a short script. Reply in ≤5 lines. Edit only
your output files; do not commit.
