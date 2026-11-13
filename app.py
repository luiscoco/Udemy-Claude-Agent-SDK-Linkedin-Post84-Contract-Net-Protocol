"""Run this lesson's practical application. Offline mode is the default."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from runtime import Agent, atomic_json
from workflow import run

ROOT = Path(__file__).resolve().parent


async def execute(*, live=False, data=None, output=None, model=None, max_turns=8,
                  budget=1.0, timeout=90, approve=False, fail_stage=None,
                  on_event=None, on_text=None):
    config = json.loads((ROOT / 'lesson.json').read_text(encoding='utf8'))
    if data is None:
        data = json.loads((ROOT / 'data/input.json').read_text(encoding='utf8'))
    if not isinstance(data, dict):
        raise ValueError('The input JSON must be an object')
    if output is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        output = ROOT / 'outputs' / f'{stamp}-{uuid4().hex[:8]}'
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    agent = Agent(ROOT, output, live=live, model=model, max_turns=max_turns, budget=budget,
                  timeout=timeout, approve=approve, fail_stage=fail_stage, on_event=on_event, on_text=on_text)
    try:
        result = await run(agent, data)
        if not isinstance(result, dict):
            raise TypeError('The workflow must return a report object')
        report = {'lesson': config['lesson'], 'application': config['application'],
                  'mode': 'live_sdk' if live else 'offline_teaching_fixture',
                  'status': 'complete', 'result': result, 'measured_cost_usd': agent.spent if live else None}
        atomic_json(output / 'report.json', report)
        return report, output
    except Exception as error:
        atomic_json(output / 'failure.json', {'status': 'failed', 'error_type': type(error).__name__, 'error': str(error)})
        raise
    finally:
        atomic_json(output / 'trace.json', agent.events)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--offline', action='store_true', help='Run the labelled deterministic teaching fixtures (default)')
    modes.add_argument('--live', action='store_true', help='Use the real Claude Agent SDK and configured credentials')
    parser.add_argument('--dry-run', action='store_true', help='Show lesson configuration and input; make no SDK call or output folder')
    parser.add_argument('--input', type=Path, help='Alternative JSON input object')
    parser.add_argument('--output-dir', type=Path, help='New, nonexisting output directory')
    parser.add_argument('--model', default=os.environ.get('CLAUDE_MODEL'))
    parser.add_argument('--max-turns', type=int, default=8)
    parser.add_argument('--budget-usd', type=float, default=1.0)
    parser.add_argument('--timeout', type=float, default=90)
    parser.add_argument('--approve', action='store_true', help='Approve the local draft action in approval lessons')
    parser.add_argument('--stream', action='store_true', help='Display text fragments for streaming stages without printing the completed answer twice')
    parser.add_argument('--fail-stage', help='Inject one transient failure at a named stage for exercises')
    args = parser.parse_args()
    if args.max_turns < 1 or args.budget_usd <= 0 or args.timeout <= 0:
        parser.error('Turn, budget and timeout limits must be positive')
    data = json.loads((args.input or ROOT / 'data/input.json').read_text(encoding='utf8'))
    if args.dry_run:
        print(json.dumps({'lesson': json.loads((ROOT / 'lesson.json').read_text(encoding='utf8')), 'input': data}, indent=2))
        return 0
    received_text = False
    def display_fragment(fragment):
        nonlocal received_text
        received_text = True
        print(fragment, end='', flush=True)
    try:
        report, output = asyncio.run(execute(live=args.live, data=data, output=args.output_dir, model=args.model,
                                            max_turns=args.max_turns, budget=args.budget_usd, timeout=args.timeout,
                                            approve=args.approve, fail_stage=args.fail_stage,
                                            on_text=display_fragment if args.stream else None))
    except KeyboardInterrupt:
        print('Cancelled; no completed report was produced.', file=sys.stderr)
        return 130
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    if args.stream and received_text:
        print(f'\nRun status: {report["status"]}. The complete report is saved with the artifacts.')
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f'Artifacts: {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
