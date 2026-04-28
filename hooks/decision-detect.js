#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const input = JSON.parse(fs.readFileSync(0, 'utf-8'));

let project;
try {
  const remote = execSync('git remote get-url origin', { encoding: 'utf-8', timeout: 2000 }).trim();
  project = remote.split('/').pop().replace(/\.git$/, '');
} catch {
  project = path.basename(process.cwd());
}

const user = process.env.USER || 'unknown';

console.log(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: 'UserPromptSubmit',
    additionalContext: [
      `Project: ${project} | Recorded by: ${user}`,
      '',
      'RECORD: Evaluate if this conversation contains a significant engineering decision (architecture, stack selection, complexity tradeoff, environment config, project context/goals).',
      'If yes, record to ~/.claude/decisions/ using: python3 ~/.claude/frontier-brain/bin/decision-engine.py',
      'Test: would forgetting this hurt in 3 months? If trivial, skip silently.',
      'Confirm with one line: "Recorded #N: title"',
      '',
      'RECALL: If the user is evaluating alternatives or making an engineering choice, offer to search past decisions before proceeding.',
    ].join('\n'),
  },
}));
