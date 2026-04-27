import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * session-start.js - Cross-platform entry point for Flow SessionStart hook.
 * Dispatches to .sh or .ps1 based on the operating system.
 */

const __dirname = dirname(fileURLToPath(import.meta.url));

function main() {
  const isWindows = process.platform === 'win32';
  
  // Choose the right script and interpreter
  let command;
  let args;
  
  if (isWindows) {
    // On Windows, use PowerShell for the .ps1 script
    command = 'powershell.exe';
    args = [
      '-ExecutionPolicy', 'Bypass',
      '-NoProfile',
      '-NonInteractive',
      '-File', join(__dirname, 'session-start.ps1')
    ];
  } else {
    // On Unix (Linux/macOS), use Bash for the .sh script
    command = 'bash';
    args = [join(__dirname, 'session-start.sh')];
  }

  const result = spawnSync(command, args, {
    encoding: 'utf8',
    env: process.env,
    // Use shell: true on Windows to help resolve powershell.exe if needed,
    // but false on Unix for more direct execution.
    shell: isWindows
  });

  if (result.error) {
    // If the process failed to start, emit a JSON error so the CLI can parse it
    const errorJson = JSON.stringify({
      systemMessage: `Error: Failed to execute session-start hook process. ${result.error.message}`
    });
    process.stdout.write(errorJson + '\n');
    process.exit(1);
  }

  // Output stdout (expected to be valid JSON from the sub-script)
  if (result.stdout) {
    process.stdout.write(result.stdout);
  }

  // Relay stderr to the console (Gemini CLI handles this based on debug settings)
  if (result.stderr) {
    process.stderr.write(result.stderr);
  }

  process.exit(result.status ?? 0);
}

main();
