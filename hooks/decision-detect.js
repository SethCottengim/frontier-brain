#!/usr/bin/env node
/**
 * Decision Detection Hook — UserPromptSubmit
 *
 * Scans user prompts for decision signals (commitment verbs + architecture nouns).
 * When detected, injects additionalContext instructing Claude to auto-record the ADR.
 *
 * Must complete in <100ms — regex only, no subprocess, no filesystem I/O.
 */

const fs = require('fs');

function readInput() {
  try {
    return JSON.parse(fs.readFileSync(0, 'utf-8'));
  } catch {
    return {};
  }
}

const COMMITMENT_VERBS = [
  /\blet'?s\s+go\s+with\b/i,
  /\bdecided?\s+to\s+use\b/i,
  /\bdecided?\s+(?:on|that)\b/i,
  /\bchoosing\b/i,
  /\bwe(?:'ll|\s+will)\s+use\b/i,
  /\bwe\s+should\s+use\b/i,
  /\bapproved?\b/i,
  /\badopting\b/i,
  /\bgoing\s+(?:with|for)\b/i,
  /\bswitching\s+to\b/i,
  /\bmigrating\s+to\b/i,
  /\bmoving\s+to\b/i,
  /\breplacing\s+.+\s+with\b/i,
  /\binstead\s+of\b/i,
  /\brather\s+than\b/i,
  /\bover\s+\w+\b/i,
];

const ARCHITECTURE_NOUNS = [
  /\bframework\b/i,
  /\bpattern\b/i,
  /\bapproach\b/i,
  /\bstack\b/i,
  /\barchitecture\b/i,
  /\bdatabase\b/i,
  /\bbackend\b/i,
  /\bfrontend\b/i,
  /\binfrastructure\b/i,
  /\bdeployment\b/i,
  /\bprotocol\b/i,
  /\bstrategy\b/i,
  /\bmethodology\b/i,
  /\btooling\b/i,
  /\blibrary\b/i,
  /\bpackage\b/i,
  /\bsdk\b/i,
  /\bapi\b/i,
  /\bmodel\b/i,
  /\bformat\b/i,
  /\bschema\b/i,
  /\bservice\b/i,
  /\bplatform\b/i,
  /\bpipeline\b/i,
  /\bengine\b/i,
  /\bstorage\b/i,
  /\bindex\b/i,
  /\bstate\s+management\b/i,
  /\bauth(?:entication|orization)?\b/i,
];

const FALSE_POSITIVE_FILTERS = [
  /\blet'?s\s+go\s+(?:to|get|eat|grab|have|take|for\s+a)\b/i,
  /\bdecided?\s+to\s+(?:take\s+a|go\s+for\s+a|eat|sleep|rest|stop|pause|leave|quit)\b/i,
  /\bwhat\s+(?:do\s+you\s+think|should\s+we|about)\b/i,
  /\bcan\s+you\s+explain\b/i,
  /\bhow\s+does\b/i,
  /\bshould\s+we\s+consider\b/i,
];

function detectDecision(text) {
  for (const filter of FALSE_POSITIVE_FILTERS) {
    if (filter.test(text)) return false;
  }

  let hasCommitment = false;
  for (const verb of COMMITMENT_VERBS) {
    if (verb.test(text)) {
      hasCommitment = true;
      break;
    }
  }
  if (!hasCommitment) return false;

  for (const noun of ARCHITECTURE_NOUNS) {
    if (noun.test(text)) return true;
  }
  return false;
}

function main() {
  const input = readInput();
  if (input.hook_event_name !== 'UserPromptSubmit') return;

  const message = (input.user_message || '').trim();
  if (!message || message.length < 10) return;

  if (detectDecision(message)) {
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'UserPromptSubmit',
        additionalContext: [
          'Decision detected in user message. Auto-record this decision using the decision-record skill:',
          '1. Run: python bin/decision-engine.py search "<topic>" to check existing ADRs',
          '2. Run: python bin/decision-engine.py next-id',
          '3. Extract context, options, decision, consequences from conversation',
          '4. Write ADR file to decisions/ADR-XXX-slug.md',
          '5. Run: python bin/decision-engine.py index',
          '6. Confirm with one line: "Recorded ADR-XXX: <title>"',
          'Do not ask for confirmation. Apply quality gate — skip if trivial.',
        ].join('\n'),
      },
    }));
  }
}

main();
